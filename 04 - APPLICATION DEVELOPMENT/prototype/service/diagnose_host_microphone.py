#!/usr/bin/env python3
"""Local-only microphone/STT isolation check; never saves captured audio.

By default, print measurements and recognized character counts only. --show-text
is intended for the controlled synthetic speaker fixture, not private speech.
No Android, classifier, references or target labels enter this diagnostic.
"""
import argparse
import json
import math
from pathlib import Path
import queue
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default='MacBook Air Microphone')
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--stt', action='store_true')
    parser.add_argument('--show-text', action='store_true')
    parser.add_argument('--wait-for-start', action='store_true', help='Load STT, then wait for Return before opening the microphone')
    parser.add_argument('--cache', type=Path, default=Path.home() / 'Library/Application Support/scam-call-alert/application-development/stt/huggingface-cache')
    args = parser.parse_args()
    if not 1 <= args.seconds <= 120:
        parser.error('--seconds must be between 1 and 120')
    import numpy as np
    import sounddevice as sd

    devices = sd.query_devices()
    matches = [i for i, d in enumerate(devices) if d['name'] == args.device and d['max_input_channels'] > 0]
    if len(matches) != 1:
        raise RuntimeError('Requested microphone must match exactly one input device')
    device = matches[0]
    recognizer = None
    if args.stt:
        from adapters import Wav2VecAdapter
        print('Loading the selected STT checkpoint; capture has not started.', flush=True)
        recognizer = Wav2VecAdapter(args.cache)
        print(json.dumps({'stt_revision': recognizer.version, 'classifier_loaded': False}), flush=True)

    if args.wait_for_start:
        input('READY_TO_START: press Return when the speaker is ready.\n')

    packets = queue.Queue(maxsize=1200)
    failures = []
    sample_rate = 16000
    def callback(data, frames, timing, status):
        if status:
            failures.append(str(status))
        try:
            packets.put_nowait(data[:, 0].copy())
        except queue.Full:
            failures.append('Capture queue overflow')

    # CoreAudio performs input conversion without changing the host hardware rate.
    settings = sd.CoreAudioSettings(change_device_parameters=False, conversion_quality='max')
    sd.check_input_settings(device=device, channels=1, dtype='int16', samplerate=sample_rate, extra_settings=settings)
    audio = np.empty(0, dtype=np.int16)
    next_end = 5 * sample_rate
    recognized = []
    total_nonzero = 0
    peak = 0
    last_report = -1
    print(json.dumps({'device': devices[device]['name'], 'hardware_default_rate_hz': devices[device]['default_samplerate'],
                      'application_rate_hz': sample_rate, 'saved_audio': False, 'duration_seconds': args.seconds}), flush=True)
    with sd.InputStream(device=device, channels=1, dtype='int16', samplerate=sample_rate,
                        blocksize=1600, extra_settings=settings, callback=callback):
        started = time.monotonic()
        print('CAPTURE_READY', flush=True)
        while time.monotonic() - started < args.seconds:
            try:
                chunk = packets.get(timeout=0.25)
            except queue.Empty:
                continue
            audio = np.concatenate((audio, chunk))
            widened = chunk.astype(np.int32)
            total_nonzero += int(np.count_nonzero(chunk))
            peak = max(peak, int(np.max(np.abs(widened))))
            second = int(time.monotonic() - started)
            if second != last_report:
                rms = math.sqrt(float(np.mean(widened.astype(np.float64) ** 2))) / 32768
                print(json.dumps({'elapsed_second': second, 'samples': len(audio), 'chunk_nonzero_samples': int(np.count_nonzero(chunk)),
                                  'peak': float(np.max(np.abs(widened))) / 32768, 'rms': rms}), flush=True)
                last_report = second
            if failures:
                raise RuntimeError('; '.join(failures))
            if recognizer is not None and len(audio) >= next_end:
                start = max(0, next_end - 5 * sample_rate)
                output = recognizer.recognize(audio[start:next_end].astype('<i2').tobytes())
                row = {'window_start_seconds': start / sample_rate, 'window_end_seconds': next_end / sample_rate,
                       'recognized_characters': len(output['text']), 'processing_seconds': output['resources']['processing_seconds']}
                if args.show_text:
                    row['text'] = output['text']
                print(json.dumps(row, ensure_ascii=False), flush=True)
                recognized.append(row)
                next_end += 4 * sample_rate
    if failures:
        raise RuntimeError('; '.join(failures))
    print(json.dumps({'capture_complete': True, 'samples_consumed': len(audio), 'nonzero_samples': total_nonzero,
                      'peak': peak / 32768, 'completed_stt_windows': len(recognized), 'saved_audio': False}), flush=True)


if __name__ == '__main__':
    main()
