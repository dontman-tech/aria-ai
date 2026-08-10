"""Web dashboard for ARIA.

A lightweight Flask web UI that provides a chat interface to ARIA,
status indicators, and a live clock — styled like a sci-fi HUD.
Runs independently of the CLI so you can interact with ARIA from a browser.
"""

from __future__ import annotations

import logging
from typing import Optional

from aria.core.assistant import ARIA

logger = logging.getLogger(__name__)


def create_app(aria: Optional[ARIA] = None) -> "Flask":
    """Create and configure the Flask web app."""
    try:
        from flask import Flask, render_template_string, request, jsonify
    except ImportError as e:
        raise ImportError("Flask is required for the web UI. Install with: pip install flask") from e

    if aria is None:
        aria = ARIA()

    app = Flask(__name__)
    app.config["aria"] = aria

    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ARIA — Advanced Reasoning & Intelligent Assistant</title>
<style>
  :root {
    --bg: #0a0e14;
    --panel: #131820;
    --accent: #00d4ff;
    --accent-dim: #006b7a;
    --text: #c9d1d9;
    --text-dim: #6b7785;
    --danger: #ff4757;
    --success: #2ed573;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', 'SF Mono', monospace;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .header {
    background: linear-gradient(135deg, var(--panel), #1a2330);
    padding: 16px 24px;
    border-bottom: 1px solid var(--accent-dim);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .logo { font-size: 24px; font-weight: bold; letter-spacing: 4px; color: var(--accent); }
  .logo span { color: var(--text); font-weight: normal; font-size: 12px; letter-spacing: 1px; }
  .status { display: flex; gap: 16px; font-size: 12px; }
  .status-item { display: flex; align-items: center; gap: 6px; }
  .dot { width: 8px; height: 8px; border-radius: 50%; }
  .dot.online { background: var(--success); box-shadow: 0 0 8px var(--success); }
  .dot.offline { background: var(--danger); }
  .chat-container {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .message {
    max-width: 75%;
    padding: 12px 16px;
    border-radius: 12px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
  }
  .message.user {
    align-self: flex-end;
    background: var(--accent-dim);
    border: 1px solid var(--accent);
  }
  .message.aria {
    align-self: flex-start;
    background: var(--panel);
    border: 1px solid var(--accent-dim);
  }
  .message .label { font-size: 11px; color: var(--text-dim); margin-bottom: 4px; }
  .input-bar {
    background: var(--panel);
    padding: 16px 24px;
    border-top: 1px solid var(--accent-dim);
    display: flex;
    gap: 12px;
  }
  .input-bar input {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--accent-dim);
    color: var(--text);
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 15px;
    font-family: inherit;
  }
  .input-bar input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(0,212,255,0.15); }
  .input-bar button {
    background: var(--accent);
    color: var(--bg);
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: bold;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.2s;
  }
  .input-bar button:hover { box-shadow: 0 0 12px var(--accent); }
  .timestamp { font-size: 11px; color: var(--text-dim); margin-top: 4px; }
  .typing { color: var(--accent); font-style: italic; }
  @media (max-width: 600px) { .message { max-width: 90%; } .status { display: none; } }
</style>
</head>
<body>
  <div class="header">
    <div class="logo">ARIA <span>Advanced Reasoning & Intelligent Assistant</span></div>
    <div class="status">
      <div class="status-item"><div class="dot {{ 'online' if brain_online else 'offline' }}"></div>Brain</div>
      <div class="status-item"><div class="dot {{ 'online' if voice_online else 'offline' }}"></div>Voice</div>
      <div class="status-item"><span id="clock">--:--:--</span></div>
    </div>
  </div>
  <div class="chat-container" id="chat">
    <div class="message aria">
      <div class="label">ARIA</div>
      ARIA online. How can I help you, Boss?
    </div>
  </div>
  <div class="input-bar">
    <input type="text" id="input" placeholder="Ask ARIA anything..." autocomplete="off" autofocus>
    <button onclick="send()">Send</button>
  </div>
<script>
  const chat = document.getElementById('chat');
  const input = document.getElementById('input');
  const brainOnline = {{ 'true' if brain_online else 'false' }};

  function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = 'message ' + sender;
    div.innerHTML = '<div class="label">' + (sender === 'user' ? '🧑 YOU' : '🤖 ARIA') + '</div>' + text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  function send() {
    const text = input.value.trim();
    if (!text) return;
    addMessage(escapeHtml(text), 'user');
    input.value = '';
    const typing = document.createElement('div');
    typing.className = 'message aria typing';
    typing.id = 'typing';
    typing.textContent = 'ARIA is thinking...';
    chat.appendChild(typing);
    chat.scrollTop = chat.scrollHeight;

    fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    })
    .then(r => r.json())
    .then(data => {
      document.getElementById('typing')?.remove();
      addMessage(escapeHtml(data.response), 'aria');
    })
    .catch(err => {
      document.getElementById('typing')?.remove();
      addMessage('Connection error: ' + err, 'aria');
    });
  }

  function escapeHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
            .replace(/\\n/g,'<br>');
  }

  input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });

  // Live clock
  function updateClock() {
    document.getElementById('clock').textContent = new Date().toLocaleTimeString();
  }
  setInterval(updateClock, 1000);
  updateClock();
</script>
</body>
</html>
    """

    @app.route("/")
    def index():
        aria = app.config["aria"]
        return render_template_string(
            HTML_TEMPLATE,
            brain_online=aria.brain.available,
            voice_online=bool(aria.stt and aria.stt.available),
        )

    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.get_json()
        message = data.get("message", "")
        aria = app.config["aria"]
        try:
            response = aria.process(message)
            return jsonify({"response": response, "success": True})
        except Exception as e:
            return jsonify({"response": f"Error: {e}", "success": False}), 500

    @app.route("/api/status")
    def status():
        aria = app.config["aria"]
        return jsonify({
            "brain_online": aria.brain.available,
            "voice_available": bool(aria.stt and aria.stt.available),
            "skills": aria.router.list_skills(),
            "memory_entries": len(aria.memory.history),
        })

    return app


def run_web(host: str = "0.0.0.0", port: int = 5000, aria: Optional[ARIA] = None) -> None:
    """Run the ARIA web dashboard."""
    app = create_app(aria)
    logger.info("Starting ARIA web dashboard on http://%s:%d", host, port)
    print(f"🌐 ARIA web dashboard starting at http://localhost:{port}")
    app.run(host=host, port=port, debug=False)


def run_web_cli() -> None:
    """CLI entry point for the web dashboard."""
    import argparse

    parser = argparse.ArgumentParser(description="ARIA Web Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", "-p", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--config", "-c", default=None, help="Path to config file")
    args = parser.parse_args()

    from aria.core.config import Config

    config = Config.from_file(args.config)
    config.voice.enabled = False  # Web UI is text-based
    aria = ARIA(config)
    run_web(host=args.host, port=args.port, aria=aria)


if __name__ == "__main__":
    run_web_cli()
