"""Independent reviewer checks using small CPU tensors, never pretrained weights."""
import copy
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
import torch
from torch.nn import functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import trainer


class TinyClassifier(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.classifier = torch.nn.Linear(3, 2)

    def forward(self, features):
        return SimpleNamespace(logits=self.classifier(features))


def collate(items, tokenizer, torch_module):
    return {
        "inputs": {"features": torch_module.tensor([item["features"] for item in items], dtype=torch.float32)},
        "labels": torch_module.tensor([item["label"] for item in items]),
        "sample_ids": [item["sample_id"] for item in items],
        "sources": [item["source_dataset"] for item in items],
    }


@pytest.mark.parametrize("sizes", [(2, 1, 2), (1, 1), (3, 2)])
def test_actual_conversation_weighted_accumulation_matches_full_batch(monkeypatch, sizes):
    monkeypatch.setattr(trainer, "pad_collate", collate)
    torch.manual_seed(67)
    accumulated = TinyClassifier()
    full = copy.deepcopy(accumulated)
    count = sum(sizes)
    items = [{"features": [i / 3, 1.0, (i % 3) / 2], "label": i % 2,
              "sample_id": f"synthetic-{i}", "source_dataset": "primary"} for i in range(count)]
    groups, cursor = [], 0
    for size in sizes:
        groups.append(items[cursor:cursor + size])
        cursor += size
    opt_a = torch.optim.SGD(accumulated.parameters(), lr=0.01)
    opt_b = torch.optim.SGD(full.parameters(), lr=0.01)
    batch = collate(items, None, torch)
    loss = F.cross_entropy(full(**batch["inputs"]).logits, batch["labels"])
    loss.backward()
    torch.nn.utils.clip_grad_norm_(full.parameters(), 1.0)
    opt_b.step()
    total_loss = trainer._train_group(groups, None, accumulated, opt_a,
        torch.amp.GradScaler("cpu", enabled=False), torch, F, torch.device("cpu"), "fp32",
        torch.nn.utils.clip_grad_norm_, 1.0, count)
    assert total_loss / count == pytest.approx(loss.item(), abs=1e-7)
    for left, right in zip(accumulated.parameters(), full.parameters()):
        assert torch.allclose(left, right, atol=1e-7, rtol=1e-6)


def test_nonfinite_training_logits_cannot_update_weights(monkeypatch):
    monkeypatch.setattr(trainer, "pad_collate", collate)
    model = TinyClassifier()
    before = copy.deepcopy(model.state_dict())
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    item = {"features": [float("nan"), 1.0, 2.0], "label": 0,
            "sample_id": "synthetic", "source_dataset": "primary"}
    with pytest.raises(FloatingPointError):
        trainer._train_group([[item]], None, model, optimizer,
            torch.amp.GradScaler("cpu", enabled=False), torch, F, torch.device("cpu"), "fp32",
            torch.nn.utils.clip_grad_norm_, 1.0, 1)
    assert all(torch.equal(before[key], value) for key, value in model.state_dict().items())


def test_finite_gradients_with_overflowing_total_norm_cannot_update_weights(monkeypatch):
    monkeypatch.setattr(trainer, "pad_collate", collate)
    model = TinyClassifier()
    values = torch.tensor([[1e30, 1.0, 2.0]], dtype=torch.float32)
    label = 1 - int(model(values).logits.argmax(dim=-1).item())
    before = copy.deepcopy(model.state_dict())
    item = {"features": values[0].tolist(), "label": label, "sample_id": "synthetic", "source_dataset": "primary"}
    with pytest.raises(RuntimeError, match="non-finite"):
        trainer._train_group([[item]], None, model, torch.optim.SGD(model.parameters(), lr=0.01),
            torch.amp.GradScaler("cpu", enabled=False), torch, F, torch.device("cpu"), "fp32",
            torch.nn.utils.clip_grad_norm_, 1.0, 1)
    assert all(torch.equal(before[key], value) for key, value in model.state_dict().items())


def test_fp16_overflow_retries_same_group_before_returning_success(monkeypatch):
    monkeypatch.setattr(trainer, "pad_collate", collate)

    class OverflowOnceScaler:
        def __init__(self):
            self.enabled = True
            self.scale_value = 8.0
            self.unscale_calls = 0
            self.step_calls = 0

        def get_scale(self):
            return self.scale_value

        def is_enabled(self):
            return self.enabled

        def scale(self, loss):
            return loss

        def unscale_(self, optimizer):
            self.unscale_calls += 1
            if self.unscale_calls == 1:
                next(parameter for group in optimizer.param_groups
                     for parameter in group["params"] if parameter.grad is not None).grad.fill_(float("inf"))

        def step(self, optimizer):
            self.step_calls += 1
            if self.unscale_calls > 1:
                optimizer.step()

        def update(self):
            if self.unscale_calls == 1:
                self.scale_value /= 2

    model = TinyClassifier()
    before = copy.deepcopy(model.state_dict())
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    scaler = OverflowOnceScaler()
    forwards = 0
    random_draws = []
    original_forward = model.forward

    def counted_forward(*args, **kwargs):
        nonlocal forwards
        forwards += 1
        random_draws.append(torch.rand(()).item())
        return original_forward(*args, **kwargs)

    model.forward = counted_forward
    items = [{"features": [0.25, 1.0, 0.5], "label": 1,
              "sample_id": "synthetic", "source_dataset": "primary"}]
    overflow_events = []
    loss_sum = trainer._train_group([[items[0]]], None, model, optimizer, scaler,
        torch, F, torch.device("cpu"), "fp16", torch.nn.utils.clip_grad_norm_, 1.0, 1,
        on_overflow=lambda retry, old, new: overflow_events.append((retry, old, new)))

    assert loss_sum > 0
    assert forwards == 2  # The same conversation was replayed, not skipped.
    assert random_draws[0] == random_draws[1]  # Dropout/random model behavior is replayed identically.
    assert scaler.step_calls == 2
    assert overflow_events == [(1, 8.0, 4.0)]
    assert any(not torch.equal(before[key], value) for key, value in model.state_dict().items())


def test_fp16_overflow_retry_limit_fails_without_advancing_weights(monkeypatch):
    monkeypatch.setattr(trainer, "pad_collate", collate)

    class AlwaysOverflowScaler:
        enabled = True

        def __init__(self):
            self.scale_value = 65536.0
            self.step_calls = 0

        def is_enabled(self): return True
        def get_scale(self): return self.scale_value
        def scale(self, loss): return loss
        def unscale_(self, optimizer):
            next(parameter for group in optimizer.param_groups
                 for parameter in group["params"] if parameter.grad is not None).grad.fill_(float("inf"))
        def step(self, optimizer): self.step_calls += 1  # Every scaler step is skipped.
        def update(self): self.scale_value /= 2

    model = TinyClassifier()
    before = copy.deepcopy(model.state_dict())
    scaler = AlwaysOverflowScaler()
    item = {"features": [0.25, 1.0, 0.5], "label": 1,
            "sample_id": "synthetic", "source_dataset": "primary"}
    with pytest.raises(FloatingPointError, match="persisted after 8 retries"):
        trainer._train_group([[item]], None, model, torch.optim.SGD(model.parameters(), lr=0.01),
            scaler, torch, F, torch.device("cpu"), "fp16", torch.nn.utils.clip_grad_norm_, 1.0, 1)
    assert scaler.step_calls == 9  # Initial attempt plus the configured eight retries.
    assert all(torch.equal(before[key], value) for key, value in model.state_dict().items())


def test_validation_does_not_change_weights_and_keeps_actual_sample_denominator(monkeypatch):
    monkeypatch.setattr(trainer, "pad_collate", collate)
    model = TinyClassifier()
    before = copy.deepcopy(model.state_dict())
    items = [{"features": [i, 1.0, 0.5], "label": i % 2,
              "sample_id": f"synthetic-{i}", "source_dataset": "primary"} for i in range(5)]
    predictions, loss = trainer.evaluate(model, items, None, torch, F,
        torch.device("cpu"), "fp32", batch_size=2)
    batch = collate(items, None, torch)
    expected = F.cross_entropy(model(**batch["inputs"]).logits, batch["labels"]).item()
    assert loss == pytest.approx(expected, abs=1e-6)
    assert [row["sample_id"] for row in predictions] == [row["sample_id"] for row in items]
    assert all(torch.equal(before[key], value) for key, value in model.state_dict().items())
    assert all(parameter.grad is None for parameter in model.parameters())


def test_full_context_validation_checks_probability_invariants_and_exact_ids(monkeypatch):
    class FixedWindowModel(torch.nn.Module):
        def __init__(self, values):
            super().__init__()
            self.values = torch.tensor(values, dtype=torch.float32)

        def forward(self, **kwargs):
            return SimpleNamespace(logits=self.values)

    def window_collate(items, tokenizer, torch_module):
        return ({"inputs": {"features": torch_module.zeros((2, 1))},
                 "labels": torch_module.tensor([items[0]["label"]])}, [0, 0])

    monkeypatch.setattr(trainer, "pad_window_collate", window_collate)
    sample = {"sample_id": "one", "source_dataset": "primary", "label": 1,
              "chunk_count": 2, "content_token_count": 510}
    kwargs = (torch, F, torch.device("cpu"), "fp32")
    with pytest.raises(FloatingPointError, match="non-finite logits"):
        trainer.evaluate(FixedWindowModel([[float("nan"), 0.0], [0.0, 1.0]]),
            [sample], None, *kwargs, batch_size=1, pooling_method="mean")
    with pytest.raises(ValueError, match="missing, duplicate, or unexpected"):
        trainer.evaluate(FixedWindowModel([[0.0, 1.0], [0.0, 1.0]]),
            [sample, dict(sample)], None, *kwargs, batch_size=1, pooling_method="max")
