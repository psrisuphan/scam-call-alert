"""Session-bound CoreAudio capture at the selected STT's 16 kHz input rate."""
import queue
import threading
import time


class HostMicrophoneCapture:
    def __init__(self, session, config):
        self.session, self.config = session, config
        self.settings = config['microphone_capture']
        self.sample_rate = int(self.settings['sample_rate_hz'])
        self.block_samples = int(self.settings['block_samples'])
        self.packets = queue.Queue(maxsize=max(1, int(config['max_queued_audio_seconds'] * self.sample_rate // self.block_samples)))
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.stream_lock = threading.Lock()
        self.stream = None
        self.worker = None
        self.captured_samples = 0
        self.accepted_samples = 0
        self.peak = 0.0
        self.error = None
        self.origin_ns = None
        self.sequence = 0

    def snapshot(self):
        with self.lock:
            return {'active': bool(self.stream and not self.stop_event.is_set()),
                    'worker_alive': bool(self.worker and self.worker.is_alive()),
                    'captured_samples': self.captured_samples, 'accepted_samples': self.accepted_samples,
                    'queued_packets': self.packets.qsize(), 'sample_rate_hz': self.sample_rate,
                    'timestamp_origin': 'host_monotonic_callback_receipt', 'peak': self.peak,
                    'error': self.error, 'execution': 'local_service'}

    def start(self):
        import sounddevice as sd
        if self.stop_event.is_set() or self.session.state != 'active':
            raise RuntimeError('Microphone session ended before capture startup')
        devices = sd.query_devices()
        matches = [i for i, device in enumerate(devices)
                   if device['name'] == self.settings['device'] and device['max_input_channels'] > 0]
        if len(matches) != 1:
            raise RuntimeError('Configured Mac microphone is unavailable or ambiguous')
        device = matches[0]
        settings = sd.CoreAudioSettings(
            change_device_parameters=self.settings['coreaudio_change_device_parameters'],
            conversion_quality=self.settings['coreaudio_conversion_quality'])
        sd.check_input_settings(device=device, channels=1, dtype='int16', samplerate=self.sample_rate,
                                extra_settings=settings)

        def callback(data, frames, timing, status):
            if self.stop_event.is_set():
                return
            if status:
                self._signal_failure('Mac microphone capture reported an interruption')
                return
            received_ns = time.monotonic_ns()
            values = data[:, 0]
            pcm = values.astype('<i2', copy=False).tobytes()
            with self.lock:
                if self.origin_ns is None:
                    self.origin_ns = received_ns
                self.captured_samples += frames
                self.peak = max((abs(int(value)) for value in values), default=0) / 32768
            try:
                self.packets.put_nowait((received_ns, pcm))
            except queue.Full:
                self._signal_failure('Live microphone analysis cannot keep up')

        self.stream = sd.InputStream(device=device, samplerate=self.sample_rate, channels=1,
                                     dtype='int16', blocksize=self.block_samples,
                                     extra_settings=settings, callback=callback)
        self.worker = threading.Thread(target=self._consume, name='HostMicrophoneSession', daemon=True)
        self.worker.start()
        try:
            with self.stream_lock:
                if self.stop_event.is_set() or self.session.state != 'active' or self.stream is None:
                    raise RuntimeError('Microphone session ended before capture startup')
                self.stream.start()
        except Exception:
            self.stop()
            raise
        deadline = time.monotonic() + self.config['request_timeout_seconds']
        while self.origin_ns is None and not self.stop_event.is_set() and self.session.state == 'active' and time.monotonic() < deadline:
            time.sleep(0.01)
        if self.session.state != 'active':
            self.stop()
            raise RuntimeError('Microphone session ended during capture startup')
        if self.origin_ns is None or self.error is not None:
            if self.error and self.session.state == 'active':
                self.session.fail('E_MICROPHONE_CAPTURE', self.error)
            self.stop()
            raise RuntimeError(self.error or 'Mac microphone did not deliver its first audio block')

    def _signal_failure(self, message):
        with self.lock:
            if self.error is not None or self.stop_event.is_set():
                return
            self.error = message
        self.stop_event.set()

    def _consume(self):
        try:
            while True:
                if self.error:
                    if self.session.state == 'active':
                        self.session.fail('E_MICROPHONE_CAPTURE', self.error)
                    return
                if self.stop_event.is_set():
                    return
                if self.session.state not in {'active', 'finishing'}:
                    self.stop_event.set()
                    return
                try:
                    received_ns, pcm = self.packets.get(timeout=0.1)
                except queue.Empty:
                    continue
                if self.stop_event.is_set():
                    return
                count = len(pcm) // 2
                start = self.accepted_samples
                end = start + count
                origin = self.origin_ns or received_ns
                elapsed_ms = max(end / (self.sample_rate / 1000), (received_ns - origin) / 1e6)
                try:
                    self.session.accept_audio(self.sequence, start, end, pcm, elapsed_ms,
                                              (received_ns - origin) / 1e6,
                                              availability_clock='host_monotonic')
                except Exception:
                    if self.session.state == 'active':
                        self.session.fail('E_MICROPHONE_CAPTURE', 'Live microphone audio could not be accepted')
                    self.stop_event.set()
                    return
                self.sequence += 1
                self.accepted_samples = end
        finally:
            self._close_stream()
            if self.error and self.session.state == 'active':
                self.session.fail('E_MICROPHONE_CAPTURE', self.error)
            self._discard_queued_packets()

    def _close_stream(self):
        with self.stream_lock:
            stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass

    def _discard_queued_packets(self):
        while True:
            try:
                self.packets.get_nowait()
            except queue.Empty:
                break

    def stop(self):
        self.stop_event.set()
        self._discard_queued_packets()
        self._close_stream()
        worker = self.worker
        if worker and worker is not threading.current_thread():
            worker.join(timeout=2)
            if worker.is_alive():
                with self.lock:
                    if self.error is None:
                        self.error = 'Live microphone worker did not stop cleanly'
                if self.session.state == 'active':
                    self.session.fail('E_MICROPHONE_CAPTURE', self.error)
