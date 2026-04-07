from __future__ import annotations
import io
import wave
import tempfile
import os
import numpy as np
import speech_recognition as sr

SAMPLERATE = 16000


class Transcriber:
    """Converts recorded audio (numpy int16 array) to text via Google Speech API."""

    def __init__(self):
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = 300
        self._recognizer.dynamic_energy_threshold = True

    def transcribe(self, audio: np.ndarray, samplerate: int = SAMPLERATE) -> str:
        """Return transcribed text, or raise sr.UnknownValueError / sr.RequestError."""
        if len(audio) == 0:
            raise ValueError("No audio recorded")

        # Write to a temp WAV file that SpeechRecognition can read
        path = tempfile.mktemp(suffix=".wav")
        try:
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)       # 16-bit = 2 bytes
                wf.setframerate(samplerate)
                wf.writeframes(audio.tobytes())

            with sr.AudioFile(path) as source:
                audio_data = self._recognizer.record(source)

            return self._recognizer.recognize_google(audio_data)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
