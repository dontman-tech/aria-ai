"""Wake word detection for ARIA.

Detects the wake word (default: "aria") in recognized speech so ARIA
can listen passively and activate on command.
"""

from __future__ import annotations

import logging
import re

from aria.voice.stt import SpeechToText

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """Detects the configured wake word in speech."""

    def __init__(self, stt: SpeechToText, wake_word: str = "aria") -> None:
        self.stt = stt
        self.wake_word = wake_word.lower().strip()
        # Common misrecognitions to also accept
        self.aliases = {
            "aria": ["aria", "area", "ariya", "aerial", "ariel"],
            "friday": ["friday", "fri day", "free day"],
            "jarvis": ["jarvis", "jar vis", "jervis"],
        }

    def listen_for_wake(self, timeout: int | None = None) -> bool:
        """Listen continuously until the wake word is heard.

        Returns True if the wake word was detected.
        """
        if not self.stt.available:
            logger.info("STT unavailable, cannot detect wake word")
            return False

        logger.info("Listening for wake word '%s'...", self.wake_word)
        while True:
            text = self.stt.listen(timeout=timeout)
            if text is None:
                continue
            if self._matches(text):
                logger.info("Wake word detected: %s", text)
                return True

    def _matches(self, text: str) -> bool:
        """Check if text contains the wake word or an alias."""
        text_lower = text.lower()
        aliases = self.aliases.get(self.wake_word, [self.wake_word])
        return any(alias in text_lower for alias in aliases)

    def strip_wake_word(self, text: str) -> str:
        """Remove the wake word from the beginning of a command."""
        text_lower = text.lower()
        aliases = self.aliases.get(self.wake_word, [self.wake_word])
        for alias in aliases:
            pattern = rf"^\s*({re.escape(alias)})[,\s]*"
            if re.match(pattern, text_lower):
                return re.sub(pattern, "", text, count=1).strip()
        return text.strip()
