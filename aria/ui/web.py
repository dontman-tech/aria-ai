"""Web dashboard for ARIA — installable mobile PWA.

Features:
  - Chat interface to ARIA (text + voice via Web Speech API)
  - API configuration panel: enter DeepSeek API key on activation
  - Kill switch: shut down ARIA from the dashboard
  - Background listening via Web Speech API + Wake Lock + Service Worker
  - PWA: installable to home screen, works offline, standalone display
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from aria.core.assistant import ARIA

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#0a0e14">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="ARIA">
<link rel="manifest" href="/static/manifest.json">
<link rel="apple-touch-icon" href="/static/icons/icon-192.png">
<link rel="icon" type="image/png" href="/static/icons/icon-192.png">
<title>ARIA</title>
<style>
  :root {
    --bg: #0a0e14;
    --panel: #131820;
    --panel2: #1a2330;
    --accent: #00d4ff;
    --accent-dim: #006b7a;
    --text: #c9d1d9;
    --text-dim: #6b7785;
    --danger: #ff4757;
    --success: #2ed573;
    --warn: #ffa502;
    --radius: 12px;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { height: 100%; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding-top: env(safe-area-inset-top);
    padding-bottom: env(safe-area-inset-bottom);
  }
  /* Header */
  .header {
    background: linear-gradient(135deg, var(--panel), var(--panel2));
    padding: 14px 16px;
    border-bottom: 1px solid var(--accent-dim);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }
  .logo { font-size: 22px; font-weight: 800; letter-spacing: 5px; color: var(--accent); }
  .logo small { display: block; color: var(--text-dim); font-size: 9px; font-weight: 400; letter-spacing: 1px; }
  .status { display: flex; gap: 12px; font-size: 11px; align-items: center; }
  .status-item { display: flex; align-items: center; gap: 5px; }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .dot.online { background: var(--success); box-shadow: 0 0 8px var(--success); }
  .dot.offline { background: var(--danger); }
  .dot.warn { background: var(--warn); box-shadow: 0 0 8px var(--warn); }
  #clock { font-variant-numeric: tabular-nums; color: var(--text-dim); }

  /* Tab bar */
  .tabs { display: flex; background: var(--panel); border-bottom: 1px solid var(--accent-dim); flex-shrink: 0; }
  .tab {
    flex: 1; padding: 12px; text-align: center; cursor: pointer; font-size: 13px; font-weight: 600;
    color: var(--text-dim); border-bottom: 2px solid transparent; transition: all .2s;
  }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }

  /* Views */
  .view { flex: 1; overflow-y: auto; display: none; flex-direction: column; }
  .view.active { display: flex; }

  /* Chat */
  .chat-container { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  .message {
    max-width: 85%; padding: 10px 14px; border-radius: var(--radius); line-height: 1.55;
    white-space: pre-wrap; word-wrap: break-word; font-size: 15px;
  }
  .message.user { align-self: flex-end; background: var(--accent-dim); border: 1px solid var(--accent); }
  .message.aria { align-self: flex-start; background: var(--panel); border: 1px solid var(--accent-dim); }
  .message .label { font-size: 10px; color: var(--text-dim); margin-bottom: 3px; }
  .typing { color: var(--accent); font-style: italic; }
  .input-bar { background: var(--panel); padding: 10px 12px; border-top: 1px solid var(--accent-dim); display: flex; gap: 8px; flex-shrink: 0; }
  .input-bar input {
    flex: 1; background: var(--bg); border: 1px solid var(--accent-dim); color: var(--text);
    padding: 12px 14px; border-radius: 24px; font-size: 16px; font-family: inherit;
  }
  .input-bar input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(0,212,255,.15); }
  .btn-icon {
    background: var(--panel2); border: 1px solid var(--accent-dim); color: var(--accent);
    width: 46px; height: 46px; border-radius: 50%; font-size: 18px; cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all .2s; flex-shrink: 0;
  }
  .btn-icon:active { transform: scale(.92); background: var(--accent-dim); }
  .btn-icon.recording { background: var(--danger); border-color: var(--danger); animation: pulse 1.2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
  .btn-send {
    background: var(--accent); color: var(--bg); border: none; padding: 0 18px; border-radius: 24px;
    font-weight: 700; cursor: pointer; font-size: 15px; flex-shrink: 0;
  }

  /* Settings */
  .settings { padding: 20px 16px; max-width: 560px; margin: 0 auto; width: 100%; }
  .section {
    background: var(--panel); border: 1px solid var(--accent-dim); border-radius: var(--radius);
    padding: 18px; margin-bottom: 16px;
  }
  .section h2 { font-size: 15px; color: var(--accent); margin-bottom: 4px; letter-spacing: 1px; }
  .section p.desc { font-size: 12px; color: var(--text-dim); margin-bottom: 14px; }
  .field { margin-bottom: 14px; }
  .field label { display: block; font-size: 12px; color: var(--text-dim); margin-bottom: 6px; }
  .field input, .field select {
    width: 100%; background: var(--bg); border: 1px solid var(--accent-dim); color: var(--text);
    padding: 12px 14px; border-radius: 8px; font-size: 15px; font-family: inherit;
  }
  .field input:focus, .field select:focus { outline: none; border-color: var(--accent); }
  .field input[type=password] { letter-spacing: .3em; }
  .btn {
    background: var(--accent); color: var(--bg); border: none; padding: 13px 20px;
    border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 14px; width: 100%;
    transition: all .2s;
  }
  .btn:hover { box-shadow: 0 0 14px rgba(0,212,255,.4); }
  .btn:active { transform: scale(.98); }
  .btn.secondary { background: var(--panel2); color: var(--text); border: 1px solid var(--accent-dim); }
  .btn.danger { background: var(--danger); color: #fff; }
  .btn.danger:hover { box-shadow: 0 0 14px rgba(255,71,87,.5); }
  .badge {
    display: inline-block; padding: 3px 9px; border-radius: 12px; font-size: 11px; font-weight: 600;
  }
  .badge.online { background: var(--success); color: var(--bg); }
  .badge.offline { background: var(--danger); color: #fff; }
  .badge.warn { background: var(--warn); color: var(--bg); }

  /* Kill switch */
  .kill-zone { text-align: center; padding: 8px 0; }
  .kill-btn {
    background: linear-gradient(135deg, var(--danger), #c0392b); color: #fff; border: none;
    padding: 18px 28px; border-radius: 14px; font-size: 16px; font-weight: 800; cursor: pointer;
    letter-spacing: 1px; width: 100%; transition: all .2s; box-shadow: 0 4px 14px rgba(255,71,87,.3);
  }
  .kill-btn:active { transform: scale(.97); }
  .kill-confirm {
    background: var(--panel2); border: 1px solid var(--danger); border-radius: var(--radius);
    padding: 18px; margin-top: 14px; display: none;
  }
  .kill-confirm.show { display: block; }
  .killed-overlay {
    position: fixed; inset: 0; background: rgba(10,14,20,.96); z-index: 100;
    display: none; flex-direction: column; align-items: center; justify-content: center; gap: 20px;
  }
  .killed-overlay.show { display: flex; }
  .killed-overlay .icon { font-size: 64px; }
  .killed-overlay h2 { color: var(--danger); letter-spacing: 2px; }
  .killed-overlay p { color: var(--text-dim); max-width: 320px; text-align: center; }

  /* Voice / background listening */
  .listen-toggle {
    display: flex; align-items: center; justify-content: space-between; gap: 10px;
  }
  .switch { position: relative; width: 52px; height: 30px; flex-shrink: 0; }
  .switch input { opacity: 0; width: 0; height: 0; }
  .slider { position: absolute; cursor: pointer; inset: 0; background: var(--accent-dim); border-radius: 30px; transition: .3s; }
  .slider:before { content: ""; position: absolute; height: 22px; width: 22px; left: 4px; bottom: 4px; background: #fff; border-radius: 50%; transition: .3s; }
  .switch input:checked + .slider { background: var(--success); }
  .switch input:checked + .slider:before { transform: translateX(22px); }
  .hint { font-size: 11px; color: var(--text-dim); margin-top: 8px; line-height: 1.5; }

  /* Install banner */
  .install-banner {
    background: var(--panel2); border: 1px solid var(--accent); border-radius: var(--radius);
    padding: 14px 16px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;
  }
  .install-banner .icon { font-size: 24px; }
  .install-banner .text { flex: 1; font-size: 13px; }
  .install-banner button { background: var(--accent); color: var(--bg); border: none; padding: 8px 14px; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 12px; }

  @media (max-width: 600px) {
    .status .status-item:not(#clock-wrap) { display: none; }
    .logo small { display: none; }
    .message { max-width: 90%; }
  }
</style>
</head>
<body>
  <div class="header">
    <div class="logo">ARIA<small>Advanced Reasoning & Intelligent Assistant</small></div>
    <div class="status">
      <div class="status-item"><div class="dot {{ 'online' if brain_online else 'offline' }}" id="brain-dot"></div>Brain</div>
      <div class="status-item"><div class="dot {{ 'online' if voice_available else 'offline' }}" id="voice-dot"></div>Voice</div>
      <div class="status-item" id="clock-wrap"><span id="clock">--:--:--</span></div>
    </div>
  </div>

  <div class="tabs">
    <div class="tab active" data-tab="chat">💬 Chat</div>
    <div class="tab" data-tab="settings">⚙️ Settings</div>
    <div class="tab" data-tab="control">🛑 Control</div>
  </div>

  <!-- CHAT VIEW -->
  <div class="view active" id="view-chat">
    <div class="chat-container" id="chat">
      <div class="message aria"><div class="label">🤖 ARIA</div>ARIA online. How can I help you, Boss?</div>
    </div>
    <div class="input-bar">
      <button class="btn-icon" id="mic-btn" onclick="toggleVoice()" title="Voice input">🎤</button>
      <input type="text" id="input" placeholder="Ask ARIA anything..." autocomplete="off" inputmode="text">
      <button class="btn-send" onclick="send()">Send</button>
    </div>
  </div>

  <!-- SETTINGS VIEW -->
  <div class="view" id="view-settings">
    <div class="settings">
      <div class="install-banner" id="install-banner" style="display:none">
        <div class="icon">📲</div>
        <div class="text">Install ARIA as an app on your home screen for full-screen, always-on access.</div>
        <button onclick="installPWA()">Install</button>
      </div>

      <div class="section">
        <h2>🧠 DeepSeek API Configuration</h2>
        <p class="desc">Enter your DeepSeek API key to activate ARIA's conversational brain. Get a key at platform.deepseek.com. The key is stored locally on this device only.</p>
        <div class="field">
          <label>API Key</label>
          <input type="password" id="api-key" placeholder="sk-..." autocomplete="off">
        </div>
        <div class="field">
          <label>Model</label>
          <select id="model-select">
            <option value="deepseek-chat">deepseek-chat (fast, general)</option>
            <option value="deepseek-reasoner">deepseek-reasoner (advanced reasoning)</option>
          </select>
        </div>
        <button class="btn" onclick="saveApiKey()">Save & Activate</button>
        <div id="key-status" style="margin-top:12px;font-size:13px;"></div>
      </div>

      <div class="section">
        <h2>🎤 Voice & Background Listening</h2>
        <p class="desc">Let ARIA listen for the wake word even when the screen is off (requires the app to be installed).</p>
        <div class="listen-toggle">
          <div><strong style="font-size:14px;">Always listening (background)</strong>
            <div class="hint">Uses Wake Lock + Web Speech API. Say "ARIA" to activate. Note: OS battery limits may pause this.</div>
          </div>
          <label class="switch"><input type="checkbox" id="bg-listen-toggle" onchange="toggleBackgroundListen()"><span class="slider"></span></label>
        </div>
      </div>

      <div class="section">
        <h2>ℹ️ System Status</h2>
        <div id="sys-status" style="font-size:13px;line-height:1.8;"></div>
      </div>
    </div>
  </div>

  <!-- CONTROL / KILL SWITCH VIEW -->
  <div class="view" id="view-control">
    <div class="settings">
      <div class="section">
        <h2>🛑 Kill Switch</h2>
        <p class="desc">Activate the kill switch to immediately shut down ARIA. This stops all processing, voice, and the running server. You'll need to restart the service manually.</p>
        <div class="kill-zone">
          <button class="kill-btn" onclick="confirmKill()">⚠️ SHUT DOWN ARIA</button>
        </div>
        <div class="kill-confirm" id="kill-confirm">
          <p style="color:var(--text);margin-bottom:14px;text-align:center;">Are you sure? This will terminate ARIA immediately and cannot be undone from the dashboard.</p>
          <div style="display:flex;gap:10px;">
            <button class="btn secondary" onclick="cancelKill()" style="flex:1;">Cancel</button>
            <button class="btn danger" onclick="executeKill()" style="flex:1;">Confirm Kill</button>
          </div>
        </div>
      </div>
      <div class="section">
        <h2>📊 Runtime Status</h2>
        <div id="runtime-status" style="font-size:13px;line-height:1.8;"></div>
      </div>
    </div>
  </div>

  <!-- Killed overlay -->
  <div class="killed-overlay" id="killed-overlay">
    <div class="icon">💀</div>
    <h2>ARIA TERMINATED</h2>
    <p>ARIA has been shut down via the kill switch. Restart the ARIA service to bring it back online, Boss.</p>
  </div>

<script>
  const brainOnline = {{ 'true' if brain_online else 'false' }};
  const voiceAvailable = {{ 'true' if voice_available else 'false' }};
  let recognition = null;
  let isRecording = false;
  let wakeLock = null;
  let bgListening = false;

  // --- Tab switching ---
  document.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
      document.querySelectorAll('.view').forEach(x => x.classList.remove('active'));
      t.classList.add('active');
      document.getElementById('view-' + t.dataset.tab).classList.add('active');
      if (t.dataset.tab === 'settings' || t.dataset.tab === 'control') refreshStatus();
    });
  });

  // --- Chat ---
  const chat = document.getElementById('chat');
  const input = document.getElementById('input');
  function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = 'message ' + sender;
    div.innerHTML = '<div class="label">' + (sender === 'user' ? '🧑 YOU' : '🤖 ARIA') + '</div>' + escapeHtml(text);
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }
  function send(text) {
    text = (text !== undefined ? text : input.value).trim();
    if (!text) return;
    addMessage(text, 'user');
    input.value = '';
    const typing = document.createElement('div');
    typing.className = 'message aria typing'; typing.id = 'typing'; typing.textContent = 'ARIA is thinking...';
    chat.appendChild(typing); chat.scrollTop = chat.scrollHeight;
    fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text})})
      .then(r => r.json()).then(data => {
        document.getElementById('typing')?.remove();
        addMessage(data.response, 'aria');
      }).catch(err => { document.getElementById('typing')?.remove(); addMessage('Connection error: ' + err, 'aria'); });
  }
  function escapeHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
  }
  input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });

  // --- Voice input (Web Speech API) ---
  function initRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return null;
    const r = new SR();
    r.continuous = false; r.interimResults = false; r.lang = 'en-US';
    r.onresult = (e) => { const t = e.results[0][0].transcript; input.value = t; send(t); };
    r.onerror = (e) => { console.warn('Speech error:', e.error); stopRecording(); };
    r.onend = () => stopRecording();
    return r;
  }
  function toggleVoice() {
    if (isRecording) { recognition?.stop(); stopRecording(); return; }
    recognition = initRecognition();
    if (!recognition) { alert('Voice input not supported in this browser, Boss.'); return; }
    recognition.start(); isRecording = true;
    document.getElementById('mic-btn').classList.add('recording');
  }
  function stopRecording() { isRecording = false; document.getElementById('mic-btn').classList.remove('recording'); }

  // --- Background listening (wake word) ---
  async function toggleBackgroundListen() {
    const enabled = document.getElementById('bg-listen-toggle').checked;
    bgListening = enabled;
    if (enabled) { await startBackgroundListen(); } else { stopBackgroundListen(); }
  }
  async function startBackgroundListen() {
    // Acquire a wake lock to keep the screen/CPU alive
    try { if ('wakeLock' in navigator) { wakeLock = await navigator.wakeLock.request('screen'); } } catch(e) { console.warn('Wake lock failed', e); }
    startWakeLoop();
  }
  function stopBackgroundListen() {
    if (wakeLock) { wakeLock.release(); wakeLock = null; }
    bgListening = false;
  }
  function startWakeLoop() {
    if (!bgListening) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('Background listening needs the Web Speech API, Boss.'); document.getElementById('bg-listen-toggle').checked = false; bgListening = false; return; }
    const r = new SR();
    r.continuous = true; r.interimResults = true; r.lang = 'en-US';
    r.onresult = (e) => {
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const transcript = e.results[i][0].transcript.toLowerCase();
        if (transcript.includes('aria')) {
          r.stop();
          // Grab the command after the wake word
          const cmd = transcript.split('aria').pop().trim();
          if (cmd) send(cmd); else addMessage('Yes, Boss?', 'aria');
          setTimeout(() => { if (bgListening) startWakeLoop(); }, 800);
          return;
        }
      }
    };
    r.onerror = () => {};
    r.onend = () => { if (bgListening) setTimeout(startWakeLoop, 300); };
    try { r.start(); } catch(e) { setTimeout(() => { if (bgListening) startWakeLoop(); }, 1000); }
  }

  // --- API Key ---
  function saveApiKey() {
    const key = document.getElementById('api-key').value.trim();
    const model = document.getElementById('model-select').value;
    if (!key) { document.getElementById('key-status').innerHTML = '<span class="badge offline">Enter a key first</span>'; return; }
    fetch('/api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({provider:'deepseek', api_key:key, model:model})})
      .then(r => r.json()).then(data => {
        if (data.online) {
          document.getElementById('key-status').innerHTML = '<span class="badge online">✓ ARIA online</span> Brain activated with ' + data.model;
          document.getElementById('brain-dot').className = 'dot online';
        } else {
          document.getElementById('key-status').innerHTML = '<span class="badge offline">✗ Key saved but brain offline</span> ' + (data.error || 'Check your key.');
        }
      }).catch(err => { document.getElementById('key-status').innerHTML = '<span class="badge offline">Error: ' + err + '</span>'; });
  }

  // --- Status ---
  function refreshStatus() {
    fetch('/api/status').then(r => r.json()).then(data => {
      const brainBadge = data.brain_online ? '<span class="badge online">ONLINE</span>' : '<span class="badge offline">OFFLINE</span>';
      const voiceBadge = data.voice_available ? '<span class="badge online">YES</span>' : '<span class="badge warn">NO</span>';
      const killedBadge = data.killed ? '<span class="badge offline">KILLED</span>' : '<span class="badge online">ACTIVE</span>';
      document.getElementById('sys-status').innerHTML =
        'Brain: ' + brainBadge + ' (' + data.provider + ' / ' + data.model + ')<br>' +
        'API Key: ' + (data.has_api_key ? '<span class="badge online">SET</span>' : '<span class="badge warn">NOT SET</span>') + '<br>' +
        'Voice: ' + voiceBadge + '<br>' +
        'Skills: ' + data.skills.join(', ') + '<br>' +
        'Memory entries: ' + data.memory_entries;
      document.getElementById('runtime-status').innerHTML =
        'ARIA Status: ' + killedBadge + '<br>Brain: ' + brainBadge + '<br>Provider: ' + data.provider + '<br>Model: ' + data.model;
      if (data.killed) showKilled();
    });
  }

  // --- Kill Switch ---
  function confirmKill() { document.getElementById('kill-confirm').classList.add('show'); }
  function cancelKill() { document.getElementById('kill-confirm').classList.remove('show'); }
  function executeKill() {
    fetch('/api/kill', {method:'POST'}).then(r => r.json()).then(data => {
      showKilled();
    }).catch(() => showKilled());
  }
  function showKilled() {
    document.getElementById('killed-overlay').classList.add('show');
    document.getElementById('kill-confirm').classList.remove('show');
  }

  // --- PWA install ---
  let deferredPrompt = null;
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferredPrompt = e; document.getElementById('install-banner').style.display = 'flex'; });
  function installPWA() {
    if (!deferredPrompt) { alert('Install via your browser menu: "Add to Home Screen", Boss.'); return; }
    deferredPrompt.prompt(); deferredPrompt.userChoice.then(() => { deferredPrompt = null; document.getElementById('install-banner').style.display = 'none'; });
  }

  // --- Service worker registration ---
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').catch(err => console.warn('SW registration failed', err));
  }

  // --- Clock ---
  function updateClock() { document.getElementById('clock').textContent = new Date().toLocaleTimeString(); }
  setInterval(updateClock, 1000); updateClock();

  // Poll status every 10s to detect kill switch
  setInterval(() => { fetch('/api/status').then(r => r.json()).then(d => { if (d.killed) showKilled(); }).catch(()=>{}); }, 10000);
</script>
</body>
</html>
"""


def create_app(aria: Optional[ARIA] = None) -> "Flask":
    """Create and configure the Flask web app (PWA dashboard)."""
    try:
        from flask import Flask, render_template_string, request, jsonify, send_from_directory
    except ImportError as e:
        raise ImportError("Flask is required for the web UI. Install with: pip install flask") from e

    if aria is None:
        aria = ARIA()

    app = Flask(__name__, static_folder=None)
    app.config["aria"] = aria

    @app.route("/")
    def index():
        return render_template_string(
            HTML_TEMPLATE,
            brain_online=aria.brain.available,
            voice_available=bool(aria.stt and aria.stt.available),
        )

    @app.route("/static/<path:filename>")
    def serve_static(filename):
        return send_from_directory(str(STATIC_DIR), filename)

    @app.route("/api/chat", methods=["POST"])
    def chat():
        if aria.killed:
            return jsonify({"response": "ARIA has been shut down via the kill switch.", "success": False, "killed": True}), 503
        data = request.get_json() or {}
        message = data.get("message", "")
        try:
            response = aria.process(message)
            return jsonify({"response": response, "success": True, "killed": aria.killed})
        except Exception as e:
            return jsonify({"response": f"Error: {e}", "success": False}), 500

    @app.route("/api/config", methods=["POST"])
    def set_config():
        data = request.get_json() or {}
        provider = data.get("provider", "deepseek")
        api_key = data.get("api_key", "")
        model = data.get("model", "deepseek-chat")
        if not api_key:
            return jsonify({"online": False, "error": "No API key provided"}), 400
        try:
            result = aria.set_api_key(provider, api_key, model)
            return jsonify(result)
        except Exception as e:
            return jsonify({"online": False, "error": str(e)}), 500

    @app.route("/api/kill", methods=["POST"])
    def kill():
        msg = aria.kill()
        return jsonify({"killed": True, "message": msg})

    @app.route("/api/status")
    def status():
        cfg = aria.get_config_status()
        return jsonify({
            "brain_online": cfg["brain_online"],
            "voice_available": cfg["voice_available"],
            "skills": aria.router.list_skills(),
            "memory_entries": len(aria.memory.history),
            "provider": cfg["provider"],
            "model": cfg["model"],
            "has_api_key": cfg["has_api_key"],
            "killed": cfg["killed"],
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
