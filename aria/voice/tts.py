"""Text-to-Speech (TTS) for ARIA.

Supports multiple engines with graceful fallback:
  - pyttsx3: offline, works without network
  - gTTS: Google TTS, requires network, higher quality
  - fallback: print to stdout when no audio device is available
"""

from __future__ import annotations

import logging
import os
import tempfile
import wave
from typing import Optional

from aria.core.config import VoiceConfig

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Synthesize speech from text."""

    def __init__(self, config: VoiceConfig) -> None:
        self.config = config
        self._engine = None
        self._init_engine()

    def _init_engine(self) -> None:
        engine = self.config.tts_engine
        if engine == "pyttsx3":
            try:
                import pyttsx3

                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", self.config.voice_rate)
                self._engine.setProperty("volume", self.config.voice_volume)
                if self.config.voice_id:
                    self._engine.setProperty("voice", self.config.voice_id)
                logger.info("TTS engine: pyttsx3 (offline)")
            except Exception as e:  # pragma: no cover - env dependent
                logger.warning("pyttsx3 init failed (%s), falling back to text mode", e)
                self._engine = None
        elif engine == "gtts":
            try:
                import gtts  # noqa: F401

                logger.info("TTS engine: gTTS")
                self._engine = "gtts"
            except ImportError:
                logger.warning("gTTS not installed, falling back to text mode")
                self._engine = None
        else:
            logger.info("TTS engine: text-only (no audio)")

    def speak(self, text: str) -> None:
        """Speak the given text aloud (or print it if no audio device)."""
        if not text.strip():
            return
        # Strip markdown for cleaner speech
        clean = self._clean_text(text)
        print(f"🔊 ARIA: {clean}")

        if self._engine is None:
            return

        if self._engine == "gtts":
            self._speak_gtts(clean)
        else:
            try:
                self._engine.say(clean)
                self._engine.runAndWait()
            except Exception as e:  # pragma: no cover - env dependent
                logger.warning("TTS playback error: %s", e)

    def _speak_gtts(self, text: str) -> None:
        try:
            from gtts import gTTS
            import subprocess

            tts = gTTS(text=text, lang="en")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            tts.save(tmp_path)
            # Try common audio players
            for player in ("mpg123", "mpv", "ffplay", "aplay"):
                if _command_exists(player):
                    flag = "-nodisp -autoexit" if player == "ffplay" else ""
                    subprocess.run(
                        f"{player} {flag} {tmp_path}",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    break
            os.unlink(tmp_path)
        except Exception as e:  # pragma: no cover - env dependent
            logger.warning("gTTS playback failed: %s", e)

    @staticmethod
    def _clean_text(text: str) -> str:
        """Remove markdown formatting for natural speech."""
        for char in "*_#`>[":
            text = text.replace(char, "")
        return text.strip()

    def list_voices(self) -> list[str]:
        """List available system voices (pyttsx3 only)."""
        if self._engine and self._engine != "gtts":
            try:
                return [v.id for v in self._engine.getProperty("voices")]
            except Exception:
                pass
        return []

    def close(self) -> None:
        if self._engine and self._engine != "gtts":
            try:
                self._engine.stop()
            except Exception:
                pass


def _command_exists(cmd: str) -> bool:
    import shutil

    return shutil.which(cmd) is not None
