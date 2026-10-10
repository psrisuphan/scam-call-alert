# Scam Call Alert model card

## Status

**Template only. No candidate has been selected, final-trained, evaluated or handed off in this artifact.** Complete every evidence field from the approved development/final-evaluation artifacts before calling this a model card for a released project model.

## Intended use and limits

- Intended project input: Thai chronological, role-free dialogue text, including recognized speech supplied by a later application component.
- Intended output: project labels `Scam` and `Not Scam` with two model scores and a fixed project decision at Scam probability `>= 0.5`.
- Not established: calibrated risk, verified benign status, fraud prevention, live-phone operation, physical-phone behavior, robustness to transcription errors, or clinical/legal/financial decision suitability.
- The supplemental `Not Scam` mapping is not independently verified benign content.

## Frozen artifact record (complete from selected/final evaluation evidence)

| Field | Recorded value |
|---|---|
| Candidate / selected configuration | Pending owner-reviewed model selection |
| Base checkpoint and immutable revision | Pending |
| Final training run and model-weight SHA-256 | Pending final training |
| Tokenizer revision and configuration checksum | Pending |
| Input-preparation configuration/code checksums | Pending |
| Label mapping and threshold | `Not Scam=0`, `Scam=1`; `0.5` (frozen plan decision) |
| Source license/attribution and sharing restrictions | Pending checkpoint/repository verification |
| Runtime versions, host/device and measured resource needs | Pending compatibility check |
| Final text-test artifact identity and report | Pending final evaluation |

## Data, training and evaluation evidence

The approved design trains on marked whole conversations but app inference is role-free whole conversation. Paired marker-removal validation measures sensitivity to that representation change; it does not establish that marked training is better. A five-run caller-only comparison uses privileged source-role information and cannot establish app feasibility. The fixed prefix may discard late scam demands. Simulated/translated dialogues and the limited dataset may not represent real calls. Report class/source counts, false positives/negatives, failures, denominators and limitations from the authorized evaluation report; none are asserted here.

CV fold variation is selection evidence, not final-test uncertainty or broad robustness. The final text-test result is separate from later STT/audio-to-warning system evidence. STT accuracy, partial-context behavior, warning timing and system performance are unmeasured by this model card.

## Safe interpretation

Scores are raw model outputs and are not calibrated probabilities of fraud or validated risk guarantees. At the frozen threshold, false alarms can mislabel benign or unfamiliar conversation; missed scams can fail to warn. Classification applies only to the text supplied for that request and cannot recover omitted context. The app/system should not claim that a warning proves fraud or that a no-warning result proves safety.
