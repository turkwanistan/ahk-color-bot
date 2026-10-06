"""System-audio level meter: WASAPI loopback of the default output device,
i.e. exactly what the speakers play. Reads OS audio only -- nothing touches
the game client. A background stream keeps a short history of 20 ms RMS
blocks so a task can ask "how loud was it since t?"."""
import collections
import threading
import time

import numpy as np
import pyaudiowpatch as pa

BLOCK_S = 0.02


class LoopbackMeter:
    def __init__(self, keep_s=40):
        self._p = pa.PyAudio()
        dev = self._p.get_default_wasapi_loopback()
        self.device = dev["name"]
        rate = int(dev["defaultSampleRate"])
        self._lock = threading.Lock()
        self._levels = collections.deque(maxlen=int(keep_s / BLOCK_S))  # (ts, rms)

        def on_audio(data, frames, time_info, status):
            x = np.frombuffer(data, np.int16).astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(x * x))) if x.size else 0.0
            with self._lock:
                self._levels.append((time.time(), rms))
            return None, pa.paContinue

        # WASAPI loopback delivers nothing while the device is silent, so a
        # gap in timestamps simply means quiet
        self._stream = self._p.open(
            format=pa.paInt16, channels=dev["maxInputChannels"], rate=rate, input=True,
            input_device_index=dev["index"], frames_per_buffer=int(rate * BLOCK_S),
            stream_callback=on_audio,
        )

    def since(self, ts):
        """[(timestamp, rms)] for blocks newer than ts, oldest first."""
        with self._lock:
            return [(t, v) for t, v in self._levels if t > ts]

    def close(self):
        self._stream.stop_stream()
        self._stream.close()
        self._p.terminate()
