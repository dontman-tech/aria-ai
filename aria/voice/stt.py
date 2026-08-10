"""Speech-to-Text (STT) for ARIA.

Supports multiple recognition engines with graceful fallback:
  - Google Web Speech API (default, requires network)
  - OpenAI Whisper (local, higher accuracy)
  - CMU Sphinx (offline, lower accuracy)
  - text input fallback for headless environments
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from aria.core.config import VoiceConfig

logger = logging.getLogger(__name__)


class SpeechToText:
    """Recognize speech from microphone input."""

    def __init__(self, config: VoiceConfig) -> None:
        self.config = config
        self._recognizer = None
        self._microphone = None
        self._whisper_model = None
        self._init_recognizer()

    def _init_recognizer(self) -> None:
        try:
            import speech_recognition as sr

            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self.config.energy_threshold
            self._recognizer.pause_threshold = self.config.pause_threshold
            self._recognizer.dynamic_energy_threshold = self.config.dynamic_energy
            try:
                self._microphone = sr.Microphone()
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("STT engine: %s with microphone", self.config.stt_engine)
            except Exception as e:
                logger.warning("No microphone available (%s), STT disabled", e)
                self._microphone = None
        except ImportError:
            logger.warning("speech_recognition not installed, STT disabled")

    def _ensure_whisper(self) -> bool:
        if self._whisper_model is not None:
            return True
        try:
            import whisper

            self._whisper_model = whisper.load_model(self.config.whisper_model)
            return True
        except Exception as e:
            logger.warning("Whisper unavailable: %s", e)
            return False

    def listen(self, timeout: Optional[int] = None) -> Optional[str]:
        """Listen for a single utterance and return recognized text.

        Returns None if listening fails or nothing is heard.
        """
        if self._recognizer is None or self._microphone is None:
            logger.debug("STT not available, returning None")
            return None

        import speech_recognition as sr

        try:
            with self._microphone as source:
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            logger.warning("Listening error: %s", e)
            return None

        return self._recognize(audio)

    def recognize_from_file(self, audio_path: str) -> Optional[str]:
        """Recognize speech from an audio file."""
        if self._recognizer is None:
            return None
        import speech_recognition as sr

        try:
            with sr.AudioFile(audio_path) as source:
                audio = self._recognizer.record(source)
            return self._recognize(audio)
        except Exception as e:
            logger.warning("File recognition error: %s", e)
            return None

    def _recognize(self, audio) -> Optional[str]:
        engine = self.config.stt_engine
        try:
            if engine == "google":
                return self._recognizer.recognize_google(audio)
            elif engine == "whisper":
                if self._ensure_whisper():
                    import speech_recognition as sr

                    wav_data = audio.get_wav_data(convert_rate=16000)
                    import io
                    import wave

                    with wave.open(io.BytesIO(wav_data), "rb") as wf:
                        frames = wf.readframes(wf.getnframes())
                    import numpy as np

                    audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                    result = self._whisper_model.transcribe(audio_np)
                    return result["text"].strip()
            elif engine == "sphinx":
                return self._recognizer.recognize_sphinx(audio)
            else:
                logger.warning("Unknown STT engine: %s", engine)
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
        except sr.RequestError as e:
            logger.warning("STT request error: %s", e)
        except Exception as e:
            logger.warning("STT recognition error: %s", e)
        return None

    @property
    def available(self) -> bool:
        return self._recognizer is not None and self._microphone is not None
