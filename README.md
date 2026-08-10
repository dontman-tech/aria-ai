# ARIA — Advanced Reasoning and Intelligent Assistant

```
╔══════════════════════════════════════════════════════════╗
║    █████╗ ██████╗ ██╗    ██╗██████╗  █████╗              ║
║   ██╔══██╗██╔══██╗██║    ██║██╔══██╗██╔══██╗             ║
║   ███████║██████╔╝██║ █╗ ██║██║  ██║███████║             ║
║   ██╔══██║██╔══██╗██║███╗██║██║  ██║██╔══██║             ║
║   ██║  ██║██████╔╝╚███╔███╔╝██████╔╝██║  ██║             ║
║   ╚═╝  ╚═╝╚═════╝  ╚══╝╚══╝ ╚═════╝ ╚═╝  ╚═╝             ║
║   Advanced Reasoning & Intelligent Assistant             ║
╚══════════════════════════════════════════════════════════╝
```

A voice-enabled AI assistant inspired by **FRIDAY** from Iron Man. ARIA can hold natural conversations, execute commands, control your system, search the web, and more — all through voice or text.

## ✨ Features

### 🧠 Conversational Brain
- Natural language conversation powered by LLMs (OpenAI GPT, Anthropic Claude, or local models)
- Persistent memory — ARIA remembers your name, preferences, and past conversations
- Distinct personality: witty, efficient, and professional (addresses you as "Boss")
- Graceful offline "echo" mode for testing without an API key

### 🎤 Voice I/O
- **Speech-to-Text**: Google Web Speech API, OpenAI Whisper, or CMU Sphinx
- **Text-to-Speech**: pyttsx3 (offline) or gTTS (online, higher quality)
- **Wake word activation**: Say "ARIA" to activate hands-free
- Automatic fallback to text mode in headless environments

### 🎯 Skills (FRIDAY-style capabilities)
| Skill | What it does |
|-------|-------------|
| **System Control** | Volume, brightness, battery, CPU/RAM usage, sleep/lock |
| **Time & Date** | Current time, date, day of the week |
| **Calculator** | Math: "calculate 15 times 3", "square root of 144", "factorial of 5" |
| **Web Search** | Search the web via DuckDuckGo Instant Answers |
| **Weather** | Current weather for any location (Open-Meteo, no API key needed) |
| **File Operations** | List, find, read, and create files |
| **App Launch** | Open applications and websites |
| **Wikipedia** | Look up articles: "who is Ada Lovelace" |
| **Memory** | Remember facts: "my name is Tony", "what's my name" |
| **Jokes** | Lighten the mood |

### 🌐 Web Dashboard
A sci-fi HUD-styled web interface for browser-based interaction.

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/dontman-tech/aria-ai.git
cd aria-ai

# Install dependencies
pip install -r requirements.txt

# (Optional) System packages for voice input
# Debian/Ubuntu:
sudo apt-get install portaudio19-dev python3-pyaudio
# macOS:
brew install portaudio
```

### Set up your LLM API key (optional but recommended)

```bash
# For OpenAI
export OPENAI_API_KEY="your-key-here"

# For Anthropic Claude
export ANTHROPIC_API_KEY="your-key-here"
```

> Without an API key, ARIA runs in **echo mode** — skills still work, but general conversation is limited.

### Run ARIA

```bash
# Interactive text chat (default)
python -m aria

# Voice mode (requires microphone)
python -m aria --voice

# Single query
python -m aria --query "what's the weather in Tokyo"

# Web dashboard
python -m aria.ui.web
# Then open http://localhost:5000
```

## 💬 Usage Examples

```
🧑 You: hello
🤖 ARIA: Hello, Boss. ARIA online and ready. What can I do for you?

🧑 You: what's the weather in Tokyo?
🤖 ARIA: In Tokyo, it's 22°C with partly cloudy, wind at 12 km/h, humidity 65%, Boss.

🧑 You: calculate 15 times 3 plus 20
🤖 ARIA: That's 65, Boss.

🧑 You: who is Ada Lovelace?
🤖 ARIA: Ada Lovelace: Augusta Ada King, Countess of Lovelace...

🧑 You: my name is Tony
🤖 ARIA: Pleasure to meet you, Tony. I'll remember that.

🧑 You: what's my name?
🤖 ARIA: Your name is Tony, Boss.

🧑 You: tell me a joke
🤖 ARIA: Why did the AI cross the road? To optimize the chicken's path, Boss.

🧑 You: help
🤖 ARIA: I'm ARIA, Boss. Here's what I can do: ...
```

## ⚙️ Configuration

Edit `config/config.yaml` to customize:

- **Voice**: STT/TTS engines, wake word, audio sensitivity
- **Brain**: LLM provider, model, temperature, memory limit
- **Personality**: Name, persona, how ARIA addresses you

## 🏗️ Architecture

```
aria/
├── core/
│   ├── assistant.py    # Main orchestrator — ties everything together
│   ├── config.py       # Configuration system (YAML + defaults)
│   └── memory.py       # Short-term history + long-term profile
├── voice/
│   ├── stt.py          # Speech-to-Text (Google/Whisper/Sphinx)
│   ├── tts.py          # Text-to-Speech (pyttsx3/gTTS)
│   └── wake_word.py    # Wake word detection
├── brain/
│   └── llm.py          # LLM interface (OpenAI/Anthropic/local/echo)
├── skills/
│   ├── base.py         # Skill base class
│   ├── router.py       # Matches commands to skills
│   ├── calculator.py   # Math evaluation
│   ├── system_control  # Volume, brightness, power
│   ├── time_date.py    # Time and date
│   ├── web_search.py   # Web search
│   ├── weather.py      # Weather lookup
│   ├── files.py        # File operations
│   ├── apps.py         # App/URL launching
│   ├── wiki.py         # Wikipedia lookups
│   ├── memory_skill.py # Remember/recall facts
│   └── joke.py         # Jokes
├── ui/
│   └── web.py          # Flask web dashboard
└── utils/
    └── helpers.py      # Utility functions
```

### How it works

1. **Input**: ARIA receives text (CLI) or speech (voice mode)
2. **Skill routing**: The input is matched against registered skills by pattern and keyword confidence
3. **Execution**: If a skill matches, it executes and returns a result
4. **Brain fallback**: If no skill matches, the LLM brain generates a conversational response
5. **Memory**: Every exchange is stored in memory for context
6. **Output**: The response is displayed and/or spoken aloud

## 🧪 Testing

```bash
pip install pytest
pytest tests/ -v
```

## 🔧 Extending ARIA

### Add a new skill

```python
from aria.skills.base import Skill, SkillResult

class MySkill(Skill):
    name = "my_skill"
    description = "Does something cool"
    patterns = [r"\b(do something cool)\b"]
    keywords = ["cool thing"]

    def execute(self, text: str) -> SkillResult:
        return SkillResult(success=True, message="Done, Boss!")
```

Register it in `aria/skills/router.py`'s `register_all()` method.

### Use a local LLM (Ollama, LM Studio)

```yaml
# config/config.yaml
brain:
  provider: local
  base_url: http://localhost:11434/v1
  model: llama3
```

## 📄 License

MIT

## 🙏 Acknowledgments

Inspired by FRIDAY and JARVIS from the Marvel Cinematic Universe. This is a fan project — ARIA is not affiliated with Marvel or Disney.
