(function () {
  // ─── CONFIG ───────────────────────────────────────────────
  const API_BASE = "http://localhost:8000";
  const SCRIPT   = document.currentScript;
  const BOT_ID   = SCRIPT?.getAttribute("data-bot-id") || "";
  const BOT_NAME = SCRIPT?.getAttribute("data-bot-name") || "BotKit Assistant";
  const COLOR    = SCRIPT?.getAttribute("data-color") || "#2563eb";

  if (!BOT_ID) {
    console.error("[BotKit] Missing data-bot-id attribute.");
    return;
  }

  // ─── STYLES ───────────────────────────────────────────────
  const style = document.createElement("style");
  style.textContent = `
    #botkit-bubble {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: ${COLOR};
      color: white;
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,0.2);
      font-size: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999999;
      transition: transform 0.2s ease;
    }
    #botkit-bubble:hover {
      transform: scale(1.1);
    }
    #botkit-window {
      position: fixed;
      bottom: 90px;
      right: 24px;
      width: 360px;
      height: 520px;
      background: #fff;
      border-radius: 16px;
      box-shadow: 0 8px 40px rgba(0,0,0,0.18);
      display: flex;
      flex-direction: column;
      z-index: 999998;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      transition: opacity 0.2s ease, transform 0.2s ease;
    }
    #botkit-window.bk-hidden {
      opacity: 0;
      pointer-events: none;
      transform: translateY(16px);
    }
    #botkit-header {
      background: ${COLOR};
      color: white;
      padding: 14px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }
    #botkit-header-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    #botkit-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: rgba(255,255,255,0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
    }
    #botkit-header-info h4 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
    }
    #botkit-header-info span {
      font-size: 11px;
      opacity: 0.85;
    }
    #botkit-close {
      background: none;
      border: none;
      color: white;
      font-size: 20px;
      cursor: pointer;
      padding: 4px;
      opacity: 0.85;
    }
    #botkit-close:hover { opacity: 1; }
    #botkit-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: #f9fafb;
    }
    .bk-msg {
      display: flex;
      flex-direction: column;
      max-width: 80%;
    }
    .bk-msg.bk-user {
      align-self: flex-end;
      align-items: flex-end;
    }
    .bk-msg.bk-bot {
      align-self: flex-start;
      align-items: flex-start;
    }
    .bk-bubble {
      padding: 10px 14px;
      border-radius: 16px;
      font-size: 13px;
      line-height: 1.5;
      word-break: break-word;
    }
    .bk-user .bk-bubble {
      background: ${COLOR};
      color: white;
      border-bottom-right-radius: 4px;
    }
    .bk-bot .bk-bubble {
      background: white;
      color: #111;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .bk-bubble ul {
      margin: 6px 0 0 0;
      padding-left: 18px;
    }
    .bk-bubble li { margin-bottom: 4px; }
    .bk-time {
      font-size: 10px;
      color: #9ca3af;
      margin-top: 3px;
      padding: 0 4px;
    }
    .bk-sources {
      font-size: 11px;
      color: #6b7280;
      margin-top: 4px;
      padding: 0 4px;
    }
    .bk-sources a {
      color: ${COLOR};
      text-decoration: none;
    }
    .bk-sources a:hover { text-decoration: underline; }
    #botkit-thinking {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 10px 14px;
      background: white;
      border-radius: 16px;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
      width: fit-content;
    }
    .bk-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #9ca3af;
      animation: bk-bounce 1.2s infinite ease-in-out;
    }
    .bk-dot:nth-child(2) { animation-delay: 0.2s; }
    .bk-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bk-bounce {
      0%, 80%, 100% { transform: scale(0.7); opacity: 0.5; }
      40%           { transform: scale(1);   opacity: 1;   }
    }
    #botkit-input-area {
      display: flex;
      gap: 8px;
      padding: 12px;
      border-top: 1px solid #e5e7eb;
      background: white;
      flex-shrink: 0;
    }
    #botkit-input {
      flex: 1;
      border: 1.5px solid #e5e7eb;
      border-radius: 24px;
      padding: 8px 14px;
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s;
    }
    #botkit-input:focus { border-color: ${COLOR}; }
    #botkit-send {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: ${COLOR};
      color: white;
      border: none;
      cursor: pointer;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      transition: opacity 0.2s;
    }
    #botkit-send:hover { opacity: 0.85; }
    #botkit-send:disabled { opacity: 0.5; cursor: not-allowed; }
    #botkit-footer {
      text-align: center;
      font-size: 10px;
      color: #d1d5db;
      padding: 4px 0 8px;
      background: white;
    }
    #botkit-footer a {
      color: #d1d5db;
      text-decoration: none;
    }
    @media (max-width: 420px) {
      #botkit-window {
        width: 100vw;
        height: 100vh;
        bottom: 0;
        right: 0;
        border-radius: 0;
      }
    }
  `;
  document.head.appendChild(style);

  // ─── HTML ─────────────────────────────────────────────────
  const bubble = document.createElement("button");
  bubble.id = "botkit-bubble";
  bubble.innerHTML = "💬";
  bubble.title = "Chat with us";

  const win = document.createElement("div");
  win.id = "botkit-window";
  win.classList.add("bk-hidden");
  win.innerHTML = `
    <div id="botkit-header">
      <div id="botkit-header-left">
        <div id="botkit-avatar">🤖</div>
        <div id="botkit-header-info">
          <h4>${escBK(BOT_NAME)}</h4>
          <span>Powered by BotKit India</span>
        </div>
      </div>
      <button id="botkit-close" title="Close">✕</button>
    </div>
    <div id="botkit-messages"></div>
    <div id="botkit-input-area">
      <input id="botkit-input" type="text"
             placeholder="Ask a question..." autocomplete="off" />
      <button id="botkit-send">➤</button>
    </div>
    <div id="botkit-footer">
      Powered by <a href="#" target="_blank">BotKit India</a>
    </div>
  `;

  document.body.appendChild(bubble);
  document.body.appendChild(win);

  // ─── TOGGLE ───────────────────────────────────────────────
  let isOpen = false;

  bubble.addEventListener("click", () => {
    isOpen = !isOpen;
    win.classList.toggle("bk-hidden", !isOpen);
    bubble.innerHTML = isOpen ? "✕" : "💬";
    if (isOpen && msgContainer().children.length === 0) {
      addBotMsg("👋 Hi! I'm your website assistant. Ask me anything about this website!");
    }
    if (isOpen) {
      document.getElementById("botkit-input").focus();
    }
  });

  document.getElementById("botkit-close").addEventListener("click", () => {
    isOpen = false;
    win.classList.add("bk-hidden");
    bubble.innerHTML = "💬";
  });

  // ─── SEND ─────────────────────────────────────────────────
  document.getElementById("botkit-send").addEventListener("click", sendMsg);
  document.getElementById("botkit-input").addEventListener("keypress", e => {
    if (e.key === "Enter") sendMsg();
  });

  async function sendMsg() {
    const input = document.getElementById("botkit-input");
    const send  = document.getElementById("botkit-send");
    const q     = input.value.trim();
    if (!q) return;

    input.value = "";
    send.disabled = true;

    addUserMsg(q);
    showThinking(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bot_id: BOT_ID, question: q }),
      });

      const data = await res.json();
      showThinking(false);

      if (!res.ok) {
        addBotMsg("⚠️ " + (data.detail || "Something went wrong."));
      } else {
        addBotMsg(data.answer, data.sources || []);
      }

    } catch {
      showThinking(false);
      addBotMsg("⚠️ Cannot reach the server right now. Please try again.");
    }

    send.disabled = false;
    input.focus();
  }

  // ─── MESSAGE BUILDERS ─────────────────────────────────────
  function addUserMsg(text) {
    const div = document.createElement("div");
    div.className = "bk-msg bk-user";
    div.innerHTML = `
      <div class="bk-bubble">${escBK(text)}</div>
      <div class="bk-time">${getTimeBK()}</div>
    `;
    msgContainer().appendChild(div);
    scrollBK();
  }

  function addBotMsg(text, sources = []) {
    const div = document.createElement("div");
    div.className = "bk-msg bk-bot";

    let sourcesHtml = "";
    if (sources.length > 0) {
      const links = sources.map(s => {
        try {
          return `<a href="${s}" target="_blank">${new URL(s).hostname}</a>`;
        } catch { return ""; }
      }).filter(Boolean).join(", ");
      if (links) sourcesHtml = `<div class="bk-sources">Sources: ${links}</div>`;
    }

    div.innerHTML = `
      <div class="bk-bubble">${formatBK(text)}</div>
      ${sourcesHtml}
      <div class="bk-time">${getTimeBK()}</div>
    `;
    msgContainer().appendChild(div);
    scrollBK();
  }

  // ─── THINKING INDICATOR ───────────────────────────────────
  let thinkingEl = null;

  function showThinking(show) {
    if (show) {
      thinkingEl = document.createElement("div");
      thinkingEl.className = "bk-msg bk-bot";
      thinkingEl.innerHTML = `
        <div id="botkit-thinking">
          <div class="bk-dot"></div>
          <div class="bk-dot"></div>
          <div class="bk-dot"></div>
        </div>
      `;
      msgContainer().appendChild(thinkingEl);
      scrollBK();
    } else {
      if (thinkingEl) {
        thinkingEl.remove();
        thinkingEl = null;
      }
    }
  }

  // ─── HELPERS ──────────────────────────────────────────────
  function msgContainer() {
    return document.getElementById("botkit-messages");
  }

  function scrollBK() {
    const c = msgContainer();
    if (c) c.scrollTop = c.scrollHeight;
  }

  function getTimeBK() {
    return new Date().toLocaleTimeString("en-IN", {
      hour: "2-digit", minute: "2-digit"
    });
  }

  function escBK(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function formatBK(text) {
    let s = escBK(text);
    s = s.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\*(.*?)\*/g, "<strong>$1</strong>");
    s = s.replace(/^[-•]\s+(.+)$/gm, "<li>$1</li>");
    s = s.replace(/(<li>.*?<\/li>\n?)+/gs, "<ul>$&</ul>");
    s = s.replace(/^\d+\.\s+(.+)$/gm, "<li>$1</li>");
    s = s.replace(/\n/g, "<br>");
    return s;
  }

})();