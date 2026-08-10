# ARIA - Advanced Reasoning and Intelligent Assistant

```
 █████╗ ██████╗ ██╗    ██╗██████╗  █████╗
██╔══██╗██╔══██╗██║    ██║██╔══██╗██╔══██╗
███████║██████╔╝██║ █╗ ██║██║  ██║███████║
██╔══██║██╔══██╗██║███╗██║██║  ██║██╔══██║
██║  ██║██████╔╝╚███╔███╔╝██████╔╝██║  ██║
╚═╝  ╚═╝╚═════╝  ╚══╝╚══╝ ╚═════╝ ╚═╝  ╚═╝
 Advanced Reasoning & Intelligent Assistant
```

A voice-enabled AI assistant inspired by **FRIDAY** from Iron Man. ARIA can hold natural conversations, execute commands, control your phone, manage files, and more -- all through voice or text. Powered by **DeepSeek AI**, installable as a **mobile app (PWA)**, with a **kill switch** on the dashboard.

## Features

### Conversational Brain (DeepSeek AI)
- Natural language conversation powered by **DeepSeek** (deepseek-chat / deepseek-reasoner)
- Also supports OpenAI, Anthropic Claude, and local models (Ollama, LM Studio)
- Persistent memory -- ARIA remembers your name, preferences, and past conversations
- Distinct personality: witty, efficient, and professional (addresses you as "Boss")
- Graceful offline "echo" mode for testing without an API key
- **Enter your API key on the dashboard** -- no env vars or config files needed

### Voice I/O
- **Speech-to-Text**: Google Web Speech API, OpenAI Whisper, or CMU Sphinx
- **Text-to-Speech**: pyttsx3 (offline) or gTTS (online, higher quality)
- **Wake word activation**: Say "ARIA" to activate hands-free
- **Background listening**: Web Speech API + Wake Lock keeps ARIA listening even with screen off (in installed PWA)
- Automatic fallback to text mode in headless environments

### Skills (FRIDAY-style capabilities)
| Skill | What it does |
|-------|-------------|
| **Phone Control** | Wifi, bluetooth, brightness, flashlight, volume, battery, notifications, alarms, screenshots |
| **System Control** | Volume, brightness, battery, CPU/RAM usage, sleep/lock |
| **Time & Date** | Current time, date, day of the week |
| **Calculator** | Math: "calculate 15 times 3", "square root of 144", "factorial of 5" |
| **Web Search** | Search the web via DuckDuckGo Instant Answers |
| **Weather** | Current weather for any location (Open-Meteo, no API key needed) |
| **File Operations** | List, find, read, create, move, copy, edit, rename, delete, organize files |
| **App Launch** | Open applications and websites |
| **Wikipedia** | Look up articles: "who is Ada Lovelace" |
| **Memory** | Remember facts: "my name is Tony", "what's my name" |
| **Jokes** | Lighten the mood |

### Installable Mobile App (PWA)
- Install ARIA to your phone's home screen for full-screen, always-on access
- Works offline (service worker caches the app shell)
- Standalone display mode (no browser chrome)
- Background listening with Wake Lock (say "ARIA" to activate with screen off)
- Built-in voice input via the Web Speech API

### Kill Switch
- A prominent kill switch on the dashboard **Control** tab
- Immediately shuts down ARIA -- stops all processing, voice, and the server
- Requires manual restart to reactivate

## Quick Start

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

### Set up your DeepSeek API key

You have two options:

1. **Via the dashboard (recommended)**: Start the web dashboard, go to the Settings tab, and enter your DeepSeek API key. It gets saved locally on your device.

2. **Via environment variable**:
```bash
export DEEPSEEK_API_KEY="your-key-here"
```

Get a key at [platform.deepseek.com](https://platform.deepseek.com).

> Without an API key, ARIA runs in **echo mode** -- skills still work, but general conversation is limited.

### Run ARIA

```bash
# Interactive text chat (default)
python -m aria

# Voice mode (requires microphone)
python -m aria --voice

# Single query
python -m aria --query "what's the weather in Tokyo"

# Web dashboard (installable PWA)
python -m aria.ui.web
# Then open http://localhost:5000 on your phone or desktop browser
# Use your browser's "Add to Home Screen" to install ARIA as an app
```

## Usage Examples

```
You: hello
ARIA: Hello, Boss. ARIA online and ready. What can I do for you?

You: what's the weather in Tokyo?
ARIA: In Tokyo, it's 22C with partly cloudy, wind at 12 km/h, humidity 65%, Boss.

You: calculate 15 times 3 plus 20
ARIA: That's 65, Boss.

You: who is Ada Lovelace?
ARIA: Ada Lovelace: Augusta Ada King, Countess of Lovelace...

You: my name is Tony
ARIA: Pleasure to meet you, Tony. I'll remember that.

You: what's my name?
ARIA: Your name is Tony, Boss.

You: move file report.txt to archive folder
ARIA: Moved report.txt to archive/, Boss.

You: turn on wifi on my phone
ARIA: Wifi is now on, Boss.

You: tell me a joke
ARIA: Why did the AI cross the road? To optimize the chicken's path, Boss.

You: help
ARIA: I'm ARIA, Boss. Here's what I can do: ...
```

## Configuration

Edit `config/config.yaml` to customize:

- **Voice**: STT/TTS engines, wake word, audio sensitivity
- **Brain**: LLM provider (deepseek/openai/anthropic/local/echo), model, temperature, memory limit
- **Personality**: Name, persona, how ARIA addresses you

## Architecture

```
aria/
  core/
    assistant.py    # Main orchestrator -- ties everything together
    config.py       # Configuration system (YAML + runtime API keys)
    memory.py       # Short-term history + long-term profile
  voice/
    stt.py          # Speech-to-Text (Google/Whisper/Sphinx)
    tts.py          # Text-to-Speech (pyttsx3/gTTS)
    wake_word.py    # Wake word detection
  brain/
    llm.py          # LLM interface (DeepSeek/OpenAI/Anthropic/local/echo)
  skills/
    base.py         # Skill base class
    router.py       # Matches commands to skills
    phone_control   # Phone: wifi, bluetooth, brightness, flashlight, etc.
    calculator.py   # Math evaluation
    system_control  # Volume, brightness, power
    time_date.py    # Time and date
    web_search.py   # Web search
    weather.py      # Weather lookup
    files.py        # File operations (list, read, move, copy, edit, delete, organize)
    apps.py         # App/URL launching
    wiki.py         # Wikipedia lookups
    memory_skill.py # Remember/recall facts
    joke.py         # Jokes
  ui/
    web.py          # Flask PWA web dashboard
    static/
      manifest.json # PWA manifest
      sw.js         # Service worker
      icons/        # App icons (192px, 512px)
  utils/
    helpers.py      # Utility functions
```

### How it works

1. **Input**: ARIA receives text (CLI/web) or speech (voice mode)
2. **Skill routing**: The input is matched against registered skills by pattern and keyword confidence
3. **Execution**: If a skill matches, it executes and returns a result
4. **Brain fallback**: If no skill matches, the DeepSeek LLM generates a conversational response
5. **Memory**: Every exchange is stored in memory for context
6. **Output**: The response is displayed and/or spoken aloud

## Testing

```bash
pip install pytest
pytest tests/ -v
```

## Extending ARIA

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

### Use a different LLM provider

```yaml
# config/config.yaml
brain:
  provider: openai          # or anthropic, local, echo
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY
```

Or use a local LLM (Ollama, LM Studio):

```yaml
brain:
  provider: local
  base_url: http://localhost:11434/v1
  model: llama3
```

## Phone Companion App

To enable full phone control (wifi, bluetooth, flashlight, etc.), the ARIA companion app bridges commands from the web dashboard to your phone's hardware. The companion app runs a local HTTP bridge that ARIA's `phone_control` skill detects automatically.

Install the companion app on your Android phone, grant the necessary permissions, and ARIA will be able to:
- Toggle wifi, bluetooth, airplane mode, flashlight, do-not-disturb
- Set brightness and volume
- Read battery status
- Send notifications, set alarms, take screenshots
- Open apps and manage files

## License

MIT

## Acknowledgments

Inspired by FRIDAY and JARVIS from the Marvel Cinematic Universe. This is a fan project -- ARIA is not affiliated with Marvel or Disney.
