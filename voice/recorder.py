from __future__ import annotations
import threading
import numpy as np
import sounddevice as sd

SAMPLERATE = 16000
CHANNELS = 1
DTYPE = "int16"


class AudioRecorder:
    """Records audio from the default mic until stop() is called."""

    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self.is_recording = False

    def start(self) -> None:
        self._chunks = []
        self.is_recording = True
        self._stream = sd.InputStream(
            samplerate=SAMPLERATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
            blocksize=1024,
        )
        self._stream.start()

    def stop(self) -> tuple[np.ndarray, int]:
        """Stop recording and return (audio_array, samplerate)."""
        self.is_recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if self._chunks:
                audio = np.concatenate(self._chunks, axis=0).flatten()
            else:
                audio = np.zeros(0, dtype=DTYPE)
        return audio, SAMPLERATE

    def _callback(self, indata: np.ndarray, frames, time, status) -> None:
        with self._lock:
            self._chunks.append(indata.copy())
