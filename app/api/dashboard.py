"""Live conversation dashboard routes."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.voice.realtime_handler import dashboard_connections

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Single-page dashboard (no framework — pure HTML/CSS/JS)
# ---------------------------------------------------------------------------

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Sears Home Services — Live Agent Dashboard</title>
<style>
  :root {
    --sears-blue: #003366;
    --accent:     #0066cc;
    --green:      #2e7d32;
    --red:        #c62828;
    --orange:     #ef6c00;
    --bg:         #f4f6f8;
    --card:       #ffffff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
         background: var(--bg); color: #333; }

  /* Header */
  .header {
    background: var(--sears-blue);
    color: #fff;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .header h1 { font-size: 20px; font-weight: 600; }
  .status-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 13px; padding: 4px 12px; border-radius: 20px;
    background: rgba(255,255,255,0.15);
  }
  .status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #66bb6a; animation: pulse 2s infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

  /* Layout */
  .container { display: grid; grid-template-columns: 1fr 340px;
               gap: 16px; padding: 16px; max-width: 1400px; margin: 0 auto; }

  /* Card */
  .card {
    background: var(--card);
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    overflow: hidden;
  }
  .card-header {
    padding: 12px 16px;
    font-weight: 600;
    font-size: 14px;
    color: var(--sears-blue);
    border-bottom: 1px solid #eee;
    display: flex; align-items: center; gap: 8px;
  }

  /* Transcript */
  #transcript {
    padding: 16px;
    height: 520px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .msg {
    max-width: 85%;
    padding: 10px 14px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.5;
    animation: fadeIn 0.3s;
  }
  @keyframes fadeIn { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:none} }
  .msg.user {
    align-self: flex-end;
    background: #e3f2fd;
    border-bottom-right-radius: 4px;
  }
  .msg.assistant {
    align-self: flex-start;
    background: #f5f5f5;
    border-bottom-left-radius: 4px;
  }
  .msg-role {
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    margin-bottom: 2px; color: #888;
  }

  /* Side panels */
  .side { display: flex; flex-direction: column; gap: 16px; }

  /* Tools log */
  #tools-log {
    padding: 12px 16px;
    height: 200px;
    overflow-y: auto;
    font-size: 13px;
  }
  .tool-entry { margin-bottom: 8px; padding: 8px; background: #fafafa;
                border-radius: 8px; border-left: 3px solid var(--accent); }
  .tool-name { font-weight: 600; color: var(--accent); }
  .tool-result { color: #555; margin-top: 4px; font-size: 12px; }

  /* Info panel */
  .info-grid { padding: 12px 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .info-item label { font-size: 11px; color: #888; text-transform: uppercase; }
  .info-item .val { font-size: 15px; font-weight: 600; }

  /* Sentiment */
  .sentiment-bar {
    height: 6px; border-radius: 3px; background: #e0e0e0;
    margin: 8px 16px 12px;
    overflow: hidden;
  }
  .sentiment-fill {
    height: 100%; border-radius: 3px; width: 70%;
    background: linear-gradient(90deg, var(--green), var(--green));
    transition: width 0.5s, background 0.5s;
  }

  /* Empty state */
  .empty {
    display: flex; align-items: center; justify-content: center;
    height: 100%; color: #bbb; font-size: 14px; text-align: center;
    padding: 40px;
  }

  @media (max-width: 800px) {
    .container { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<div class="header">
  <h1>Sears Home Services — Live Agent Dashboard</h1>
  <span class="status-badge">
    <span class="status-dot" id="statusDot"></span>
    <span id="statusText">Connecting…</span>
  </span>
</div>

<div class="container">
  <!-- Left: Transcript -->
  <div class="card">
    <div class="card-header">
      <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
        <path d="M8 15c4.418 0 8-3.134 8-7s-3.582-7-8-7-8 3.134-8 7c0 1.76.743
        3.37 1.97 4.6-.097 1.016-.417 2.13-.771 2.966-.079.186.074.394.273.362
        2.256-.37 3.597-.938 4.18-1.234A9 9 0 0 0 8 15z"/>
      </svg>
      Live Transcript
    </div>
    <div id="transcript">
      <div class="empty">Waiting for a call…</div>
    </div>
  </div>

  <!-- Right: side panels -->
  <div class="side">
    <!-- Call info -->
    <div class="card">
      <div class="card-header">Call Info</div>
      <div class="info-grid">
        <div class="info-item">
          <label>Status</label>
          <div class="val" id="callStatus">No active call</div>
        </div>
        <div class="info-item">
          <label>Duration</label>
          <div class="val" id="callDuration">—</div>
        </div>
        <div class="info-item">
          <label>Call SID</label>
          <div class="val" id="callSid" style="font-size:11px;word-break:break-all;">—</div>
        </div>
        <div class="info-item">
          <label>Turns</label>
          <div class="val" id="turnCount">0</div>
        </div>
      </div>
      <div class="card-header" style="border-top:1px solid #eee;">Sentiment</div>
      <div class="sentiment-bar"><div class="sentiment-fill" id="sentimentFill"></div></div>
    </div>

    <!-- Tools -->
    <div class="card">
      <div class="card-header">
        <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
          <path d="M1 0L0 1l2.2 3.081a1 1 0 0 0 .815.419h.07a1 1 0 0 1
          .708.293l2.675 2.675-2.617 2.654A3.003 3.003 0 0 0 0 13a3 3 0
          1 0 5.878-.851l2.654-2.617.968.968-.305.914a1 1 0 0 0
          .242 1.023l3.356 3.356a1 1 0 0 0 1.414 0l1.586-1.586a1 1 0 0 0
          0-1.414l-3.356-3.356a1 1 0 0 0-1.023-.242l-.914.305-.761-.761
          2.045-2.045a.5.5 0 0 0 0-.707L8.53 2.833a.5.5 0 0 0-.707
          0L5.778 4.878 3.502 2.6 1 0z"/>
        </svg>
        Tool Calls
      </div>
      <div id="tools-log">
        <div class="empty" style="height:auto;padding:20px;">No tool calls yet</div>
      </div>
    </div>
  </div>
</div>

<script>
(function() {
  const transcript = document.getElementById('transcript');
  const toolsLog   = document.getElementById('tools-log');
  const statusDot  = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const callStatus = document.getElementById('callStatus');
  const callDuration = document.getElementById('callDuration');
  const callSidEl  = document.getElementById('callSid');
  const turnCount  = document.getElementById('turnCount');
  const sentimentFill = document.getElementById('sentimentFill');

  let turns = 0;
  let callStart = null;
  let durationTimer = null;
  let sentiment = 70;          // 0-100 scale, 70 = positive
  let firstMessage = true;

  function connect() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/dashboard/ws`);

    ws.onopen = () => {
      statusDot.style.background = '#66bb6a';
      statusText.textContent = 'Connected';
    };

    ws.onclose = () => {
      statusDot.style.background = '#ef5350';
      statusText.textContent = 'Disconnected — reconnecting…';
      setTimeout(connect, 3000);
    };

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      handleEvent(data);
    };
  }

  function handleEvent(data) {
    switch(data.type) {

      case 'call_started':
        callStatus.textContent = 'Active';
        callStatus.style.color = '#2e7d32';
        callSidEl.textContent = data.call_sid || '—';
        callStart = Date.now();
        turns = 0;
        turnCount.textContent = '0';
        if (durationTimer) clearInterval(durationTimer);
        durationTimer = setInterval(updateDuration, 1000);
        if (firstMessage) {
          transcript.innerHTML = '';
          toolsLog.innerHTML = '';
          firstMessage = false;
        }
        break;

      case 'call_ended':
        callStatus.textContent = 'Ended';
        callStatus.style.color = '#c62828';
        if (durationTimer) clearInterval(durationTimer);
        firstMessage = true;
        break;

      case 'transcript':
        addMessage(data.role, data.text);
        turns++;
        turnCount.textContent = turns;
        // Naive sentiment: detect negative keywords
        updateSentiment(data.text, data.role);
        break;

      case 'tool_call':
        addToolCall(data.tool, data.arguments);
        break;

      case 'tool_result':
        addToolResult(data.tool, data.result);
        break;
    }
  }

  function addMessage(role, text) {
    if (!text) return;
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.innerHTML = `<div class="msg-role">${role === 'user' ? 'Customer' : 'Samantha (AI)'}</div>${escapeHtml(text)}`;
    transcript.appendChild(div);
    transcript.scrollTop = transcript.scrollHeight;
  }

  function addToolCall(tool, args) {
    // Remove empty-state
    const empty = toolsLog.querySelector('.empty');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.className = 'tool-entry';
    div.id = `tool-${Date.now()}`;
    div.innerHTML = `<div class="tool-name">${escapeHtml(tool)}</div>
      <div class="tool-result" style="color:#888;">Running…</div>`;
    toolsLog.appendChild(div);
    toolsLog.scrollTop = toolsLog.scrollHeight;
  }

  function addToolResult(tool, result) {
    // Find the last tool entry without a real result
    const entries = toolsLog.querySelectorAll('.tool-entry');
    const last = entries[entries.length - 1];
    if (last) {
      const res = last.querySelector('.tool-result');
      if (res) {
        const short = (result || '').substring(0, 200);
        res.textContent = short + (result && result.length > 200 ? '…' : '');
        res.style.color = '#555';
      }
    }
  }

  function updateSentiment(text, role) {
    if (role !== 'user') return;
    const lower = (text || '').toLowerCase();
    const neg = ['frustrat','angry','annoyed','terrible','horrible','awful',
                 'worst','hate','useless','ridiculous','unacceptable','damn',
                 'hell','stupid'];
    const pos = ['thank','great','perfect','awesome','wonderful','appreciate',
                 'excellent','good','nice','helpful'];
    let delta = 0;
    neg.forEach(w => { if (lower.includes(w)) delta -= 12; });
    pos.forEach(w => { if (lower.includes(w)) delta += 8; });
    sentiment = Math.max(5, Math.min(100, sentiment + delta));
    sentimentFill.style.width = sentiment + '%';
    if (sentiment < 35) {
      sentimentFill.style.background = 'linear-gradient(90deg,#c62828,#ef5350)';
    } else if (sentiment < 60) {
      sentimentFill.style.background = 'linear-gradient(90deg,#ef6c00,#ffa726)';
    } else {
      sentimentFill.style.background = 'linear-gradient(90deg,#2e7d32,#66bb6a)';
    }
  }

  function updateDuration() {
    if (!callStart) return;
    const sec = Math.floor((Date.now() - callStart) / 1000);
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    callDuration.textContent = `${m}:${s.toString().padStart(2,'0')}`;
  }

  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str || '';
    return d.innerHTML;
  }

  connect();
})();
</script>
</body>
</html>
"""


@router.get("/")
async def dashboard_page():
    """Serve the live dashboard HTML page."""
    return HTMLResponse(content=DASHBOARD_HTML)


@router.websocket("/ws")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint that streams live conversation events to the dashboard."""
    await websocket.accept()
    dashboard_connections.add(websocket)
    logger.info("Dashboard client connected")

    try:
        # Keep the connection alive; the client doesn't send data
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        dashboard_connections.discard(websocket)
        logger.info("Dashboard client disconnected")
