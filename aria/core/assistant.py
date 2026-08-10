"""ARIA - the main assistant orchestrator.

This is the heart of ARIA. It ties together:
  - Voice I/O (speech-to-text, text-to-speech, wake word)
  - The conversational brain (LLM)
  - The skill router (command execution)
  - Conversation memory
  - A text-based CLI interface with optional voice mode
"""

from __future__ import annotations

import logging
import re
import sys
import threading
from typing import Optional

from aria.core.config import Config, PersonalityConfig, BrainConfig, VoiceConfig
from aria.core.memory import Memory
from aria.brain.llm import Brain
from aria.skills.router import SkillRouter
from aria.voice.tts import TextToSpeech
from aria.voice.stt import SpeechToText
from aria.voice.wake_word import WakeWordDetector

logger = logging.getLogger(__name__)

# Commands that should always be handled by skills, never passed to the LLM
DIRECT_COMMANDS = [
    "exit", "quit", "bye", "goodbye", "shut down", "stop",
    "help", "what can you do", "capabilities",
    "clear", "reset",
]


class ARIA:
    """The main ARIA assistant."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config.from_file()
        self._setup_logging()

        # Initialize memory
        self.memory = Memory(
            limit=self.config.brain.memory_limit,
            data_dir=self.config.data_dir,
        )

        # Initialize the brain (LLM)
        self.brain = Brain(
            brain_config=self.config.brain,
            personality=self.config.personality,
        )

        # Initialize skill router
        self.router = SkillRouter(memory=self.memory)
        self.router.register_all()

        # Initialize voice (TTS always available, STT may not be)
        self.tts = TextToSpeech(self.config.voice)
        self.stt: Optional[SpeechToText] = None
        self.wake_detector: Optional[WakeWordDetector] = None
        if self.config.voice.enabled:
            try:
                self.stt = SpeechToText(self.config.voice)
                if self.stt.available and self.config.voice.wake_word_enabled:
                    self.wake_detector = WakeWordDetector(self.stt, self.config.voice.wake_word)
            except Exception as e:
                logger.warning("Voice init failed: %s", e)

        self._running = False
        self._voice_mode = False
        logger.info("ARIA initialized. Brain: %s, Voice STT: %s", self.brain.available, self.stt is not None and self.stt.available)

    def _setup_logging(self) -> None:
        level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    @property
    def system_prompt(self) -> str:
        """Build the system prompt combining persona and skill awareness."""
        skills = self.router.list_skills()
        return (
            f"{self.config.personality.persona}\n\n"
            f"Your name is {self.config.personality.name}. "
            f"You have access to these skills/capabilities: {', '.join(skills)}. "
            f"When a user asks you to perform an action that a skill can handle, "
            f"the skill will execute automatically before you respond. "
            f"For general conversation, questions, and advice, respond naturally. "
            f"Keep responses concise and conversational unless detail is requested."
        )

    def process(self, user_input: str) -> str:
        """Process a single user input and return ARIA's response.

        This is the main entry point for both text and voice input.
        """
        user_input = user_input.strip()
        if not user_input:
            return "I didn't catch that, Boss."

        # Store in memory
        self.memory.add("user", user_input)

        # Check for direct/meta commands
        lower = user_input.lower()
        if any(lower.startswith(cmd) or lower == cmd for cmd in ["exit", "quit", "bye", "goodbye"]):
            self._running = False
            return "Goodbye, Boss. ARIA signing off."

        if lower in ("help", "what can you do", "capabilities", "what can you do?"):
            return self._help_text()

        if lower in ("clear", "reset conversation"):
            self.memory.clear()
            response = "Conversation cleared, Boss."
            self.memory.add("assistant", response)
            return response

        # Try skill routing first
        result = self.router.execute(user_input)
        if result is not None:
            response = result.message
            self.memory.add("assistant", response)
            return response

        # No skill matched — use the LLM brain for conversation
        messages = self.memory.context_messages(self.system_prompt)
        response = self.brain.respond(messages)
        self.memory.add("assistant", response)
        return response

    def _help_text(self) -> str:
        """Generate help text listing ARIA's capabilities."""
        skills = self.router.list_skills()
        lines = [
            "I'm ARIA, Boss. Here's what I can do:",
            "",
            "🎯 Skills:",
        ]
        skill_descriptions = {
            "system_control": "Control volume, brightness, get system info, battery status",
            "time_date": "Tell the time, date, or day of the week",
            "calculator": "Do math: 'calculate 15 times 3', 'what is the square root of 144'",
            "web_search": "Search the web: 'search for quantum computing'",
            "weather": "Get weather: 'weather in Tokyo'",
            "files": "List, find, read, and create files",
            "apps": "Open apps and websites: 'open chrome', 'go to github.com'",
            "wiki": "Look things up: 'who is Ada Lovelace', 'what is quantum entanglement'",
            "memory": "Remember facts: 'my name is Tony', 'what's my name'",
            "joke": "Tell a joke",
        }
        for s in skills:
            desc = skill_descriptions.get(s, "")
            lines.append(f"  • {s}: {desc}")
        lines += [
            "",
            "💬 General conversation: ask me anything and I'll converse naturally.",
            "🎤 Say 'voice mode' to switch to voice, 'text mode' to switch back.",
            "🚪 Say 'exit' to shut me down.",
        ]
        return "\n".join(lines)

    def speak(self, text: str) -> None:
        """Speak or print a response."""
        self.tts.speak(text)

    def listen(self) -> Optional[str]:
        """Listen for voice input and return recognized text."""
        if self.stt is None or not self.stt.available:
            return None
        return self.stt.listen()

    def run_cli(self, voice_mode: bool = False) -> None:
        """Run ARIA in an interactive CLI session.

        Args:
            voice_mode: If True, listen for voice input instead of text.
        """
        self._running = True
        self._voice_mode = voice_mode

        # Boot message
        boot_msg = self._boot_message()
        print(boot_msg)
        self.tts.speak("ARIA online. How can I help you, Boss?")

        while self._running:
            try:
                if self._voice_mode:
                    user_input = self._voice_input_cycle()
                else:
                    print("\n" + "─" * 50)
                    user_input = input("🧑 You: ").strip()

                if not user_input:
                    continue

                # Handle mode switching
                lower = user_input.lower()
                if "voice mode" in lower:
                    if self.stt and self.stt.available:
                        self._voice_mode = True
                        self.speak("Switching to voice mode, Boss.")
                    else:
                        print("⚠️ Voice input not available on this system. Staying in text mode.")
                    continue
                if "text mode" in lower:
                    self._voice_mode = False
                    self.speak("Switching to text mode, Boss.")
                    continue

                response = self.process(user_input)
                # Print response (speak() already prints, but we want clean display)
                if not self._voice_mode:
                    print(f"\n🤖 ARIA: {response}")
                else:
                    self.speak(response)

            except KeyboardInterrupt:
                print("\n\nShutting down...")
                break
            except EOFError:
                break
            except Exception as e:
                logger.error("Error in main loop: %s", e)
                print(f"⚠️ Something went wrong: {e}")

        self.shutdown()

    def _voice_input_cycle(self) -> str:
        """Handle one voice input cycle, including wake word."""
        if self.wake_detector and self.config.voice.wake_word_enabled:
            print(f"\n🎤 Say '{self.config.voice.wake_word}' to activate...")
            if not self.wake_detector.listen_for_wake():
                return ""
            print("🎙️  Listening...")
        else:
            print("\n🎙️  Listening... (Ctrl+C to exit)")

        text = self.listen()
        if text is None:
            return ""
        print(f"🧑 You: {text}")
        return text

    def _boot_message(self) -> str:
        """Generate a stylish boot message."""
        brain_status = "● ONLINE" if self.brain.available else "○ OFFLINE (echo mode)"
        voice_status = "● AVAILABLE" if (self.stt and self.stt.available) else "○ UNAVAILABLE"
        return f"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║    █████╗ ██████╗ ██╗    ██╗██████╗  █████╗              ║
║   ██╔══██╗██╔══██╗██║    ██║██╔══██╗██╔══██╗             ║
║   ███████║██████╔╝██║ █╗ ██║██║  ██║███████║             ║
║   ██╔══██║██╔══██╗██║███╗██║██║  ██║██╔══██║             ║
║   ██║  ██║██████╔╝╚███╔███╔╝██████╔╝██║  ██║             ║
║   ╚═╝  ╚═╝╚═════╝  ╚══╝╚══╝ ╚═════╝ ╚═╝  ╚═╝             ║
║                                                          ║
║   Advanced Reasoning & Intelligent Assistant             ║
║                                                          ║
║   Brain: {brain_status:<48s} ║
║   Voice: {voice_status:<48s} ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

    def shutdown(self) -> None:
        """Clean shutdown of all components."""
        logger.info("ARIA shutting down...")
        self.tts.close()
        self.memory._save()

    def run_single(self, query: str) -> str:
        """Process a single query without an interactive session.

        Useful for scripting and testing.
        """
        return self.process(query)


def main() -> None:
    """Entry point for running ARIA."""
    import argparse

    parser = argparse.ArgumentParser(description="ARIA - Advanced Reasoning and Intelligent Assistant")
    parser.add_argument("--config", "-c", help="Path to config file", default=None)
    parser.add_argument("--voice", "-v", action="store_true", help="Start in voice mode")
    parser.add_argument("--query", "-q", help="Run a single query and exit", default=None)
    parser.add_argument("--text", "-t", action="store_true", help="Force text-only mode (no voice)")
    args = parser.parse_args()

    config = Config.from_file(args.config)
    if args.text:
        config.voice.enabled = False

    aria = ARIA(config)

    if args.query:
        response = aria.run_single(args.query)
        print(f"🤖 ARIA: {response}")
    else:
        aria.run_cli(voice_mode=args.voice)


if __name__ == "__main__":
    main()
