# ARIA - Repository Knowledge

## Project Overview
ARIA (Advanced Reasoning and Intelligent Assistant) is a voice-enabled AI assistant inspired by FRIDAY from Iron Man. Built in Python.

## Architecture
- **core/assistant.py**: Main orchestrator that ties together voice, brain, skills, memory
- **core/config.py**: YAML-based config with env var overrides
- **core/memory.py**: Short-term conversation history + long-term user profile (JSON persistence)
- **brain/llm.py**: LLM interface supporting OpenAI, Anthropic, local (Ollama), and echo (offline) modes
- **voice/stt.py**: Speech-to-text (Google/Whisper/Sphinx)
- **voice/tts.py**: Text-to-speech (pyttsx3/gTTS) with graceful text fallback
- **voice/wake_word.py**: Wake word detection
- **skills/**: Modular skill system with pattern+keyword matching router
- **ui/web.py**: Flask web dashboard

## Key Design Patterns
- **Graceful degradation**: Every component has a fallback (no mic → text mode, no API key → echo mode)
- **Skill routing**: Skills matched by regex patterns + keywords with confidence scoring; skills take priority over LLM
- **Dependency injection**: Memory instance injected into SkillRouter and MemorySkill
- **Late imports**: Heavy/optional dependencies imported inside methods to avoid import failures

## Running
- Text mode: `python -m aria`
- Voice mode: `python -m aria --voice`
- Single query: `python -m aria -q "calculate 2+2"`
- Web UI: `python -m aria.ui.web`
- Tests: `pytest tests/ -v`

## Config
- `config/config.yaml` for all settings
- API keys via env vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- Without API key, runs in "echo mode" (skills work, conversation is canned)

## Build
- `pyproject.toml` for packaging; entry points: `aria` and `aria-web`
- `requirements.txt` for pip install
