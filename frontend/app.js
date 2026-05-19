// ========================================
// BotKit India — Frontend Logic
// ========================================

const API_BASE = "http://localhost:8000";


// ========================================
// INDEX PAGE — CREATE CHATBOT
// ========================================

async function createChatbot() {

    const urlInput = document.getElementById("website-url");
    const url = urlInput?.value.trim();

    if (!url) {
        showError("Please paste a website URL first.");
        return;
    }
    if (!url.startsWith("http")) {
        showError("URL must start with http:// or https://");
        return;
    }

    const createBtn     = document.getElementById("create-btn");
    const progressBar   = document.getElementById("progressBar");
    const progressTrack = document.getElementById("progressTrack");
    const pagesCountEl  = document.getElementById("pages-count");

    // Show loading state
    createBtn.disabled = true;
    progressTrack.classList.remove("hidden");
    progressBar.style.width = "10%";
    showStatus("🔍 Connecting to crawler...");
    hideError();

    // Fake progress animation while crawl runs in background
    const stages = [
        { pct: 12, label: "🌐 Fetching homepage…" },
        { pct: 22, label: "🕷️ Discovering internal links…" },
        { pct: 32, label: "📄 Crawling pages…" },
        { pct: 42, label: "📄 Crawling pages…" },
        { pct: 52, label: "📄 Crawling pages…" },
        { pct: 60, label: "✂️ Stripping ads & navigation…" },
        { pct: 67, label: "📝 Extracting clean content…" },
        { pct: 74, label: "🧠 Analysing text structure…" },
        { pct: 80, label: "💾 Building embeddings…" },
        { pct: 86, label: "⚙️ Storing knowledge base…" },
        { pct: 91, label: "🔗 Linking content together…" },
        { pct: 95, label: "✨ Almost ready…" },
    ];
    let stageIdx    = 0;
    let pageCounter = 0;

    const ticker = setInterval(() => {
        if (stageIdx < stages.length) {
            const { pct, label } = stages[stageIdx];
            progressBar.style.width = pct + "%";
            showStatus(label);
            pageCounter++;
            if (pagesCountEl) pagesCountEl.textContent = `Pages found: ${pageCounter}`;
            stageIdx++;
        }
    }, 1400);

    try {
        const res = await fetch(`${API_BASE}/crawl`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Crawl failed.");
        }

        const data = await res.json();
        const botId = data.bot_id;

        localStorage.setItem("bot_id", botId);
        localStorage.setItem("website_url", url);

        pollStatus(botId, ticker, progressBar, pagesCountEl);

    } catch (err) {
        clearInterval(ticker);
        createBtn.disabled = false;
        progressTrack.classList.add("hidden");
        progressBar.style.width = "0%";
        showError("⚠️ " + err.message);
    }
}


// ========================================
// POLL STATUS — check every 2s until ready
// ========================================

function pollStatus(botId, ticker, progressBar, pagesCountEl) {

    const pollInterval = setInterval(async () => {

        try {
            const res = await fetch(`${API_BASE}/status/${botId}`);
            const data = await res.json();

            if (data.pages_crawled > 0 && pagesCountEl) {
                pagesCountEl.textContent = `Pages crawled: ${data.pages_crawled}`;
            }

            if (data.status === "ready") {
                clearInterval(pollInterval);
                clearInterval(ticker);
                progressBar.style.width = "100%";
                showStatus("✅ Crawl complete!");
                if (pagesCountEl) pagesCountEl.textContent = `Pages crawled: ${data.pages_crawled}`;
                await sleep(500);
                triggerSplitLayout(data);
            }

            else if (data.status === "error") {
                clearInterval(pollInterval);
                clearInterval(ticker);
                document.getElementById("create-btn").disabled = false;
                document.getElementById("progressTrack").classList.add("hidden");
                showError("⚠️ " + (data.error || "Something went wrong during crawl."));
            }

        } catch {
            clearInterval(pollInterval);
            clearInterval(ticker);
            document.getElementById("create-btn").disabled = false;
            showError("⚠️ Lost connection to backend.");
        }

    }, 2000);
}


// ========================================
// TRIGGER SPLIT LAYOUT (after crawl done)
// ========================================

function triggerSplitLayout(data) {

    const layout       = document.getElementById("appLayout");
    const resultsPanel = document.getElementById("resultsPanel");
    const pagesBadge   = document.getElementById("pagesBadge");
    const pagesList    = document.getElementById("pagesList");

    document.getElementById("status-section").classList.add("hidden");
    document.getElementById("progressTrack").classList.add("hidden");
    document.getElementById("success-section").classList.remove("hidden");

    layout.classList.remove("state-centered");
    layout.classList.add("state-split");
    resultsPanel.classList.remove("hidden");

    const count = data.pages_crawled || 0;
    pagesBadge.textContent = `${count} page${count !== 1 ? "s" : ""}`;

    pagesList.innerHTML = "";
    const pages = data.pages || [];

    if (pages.length > 0) {
        pages.forEach((page, i) => {
            const card = document.createElement("div");
            card.className = "page-card";
            card.style.animationDelay = `${i * 0.05}s`;
            card.innerHTML = `
                <div class="page-card-url">${escapeHtml(page.url)}</div>
                <div class="page-card-preview">${escapeHtml(page.preview)}</div>
            `;
            pagesList.appendChild(card);
        });
    } else {
        const card = document.createElement("div");
        card.className = "page-card";
        card.innerHTML = `
            <div class="page-card-url">${escapeHtml(data.url || "")}</div>
            <div class="page-card-preview">
                Successfully crawled ${count} page${count !== 1 ? "s" : ""}. Your chatbot is ready!
            </div>
        `;
        pagesList.appendChild(card);
    }
}


// ========================================
// STATUS / ERROR UI HELPERS
// ========================================

function showStatus(msg) {
    const s = document.getElementById("status-section");
    const t = document.getElementById("status-text");
    if (s) s.classList.remove("hidden");
    if (t) t.textContent = msg;
}

function showError(msg) {
    const s = document.getElementById("error-section");
    const t = document.getElementById("error-text");
    if (s) s.classList.remove("hidden");
    if (t) t.textContent = msg;
}

function hideError() {
    document.getElementById("error-section")?.classList.add("hidden");
}

function goToChat() {
    window.location.href = "chat.html";
}

function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

document.getElementById("website-url")
    ?.addEventListener("keypress", e => {
        if (e.key === "Enter") createChatbot();
    });


// ========================================
// CHAT PAGE — INIT
// ========================================

function initChat() {

    const websiteUrl = localStorage.getItem("website_url");

    if (websiteUrl) {
        try {
            const hostname = new URL(websiteUrl).hostname;
            const el = document.getElementById("website-name");
            if (el) el.textContent = hostname;
        } catch {}
    }

    document.getElementById("user-input")
        ?.addEventListener("keypress", e => {
            if (e.key === "Enter") sendMessage();
        });

    document.querySelectorAll(".suggestion-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const msg = chip.getAttribute("data-msg");
            if (!msg) return;
            document.getElementById("user-input").value = msg;
            document.getElementById("suggestions")?.remove();
            sendMessage();
        });
    });

    document.getElementById("clearChatBtn")
        ?.addEventListener("click", () => {
            if (confirm("Clear conversation?")) location.reload();
        });
}


// ========================================
// CHAT — SEND MESSAGE
// ========================================

async function sendMessage() {

    const input    = document.getElementById("user-input");
    const sendBtn  = document.getElementById("send-btn");
    const question = input?.value.trim();
    if (!question) return;

    input.value = "";
    if (sendBtn) sendBtn.disabled = true;
    document.getElementById("suggestions")?.remove();

    addUserMessage(question);
    showThinking(true);

    const botId = localStorage.getItem("bot_id");

    if (!botId) {
        showThinking(false);
        if (sendBtn) sendBtn.disabled = false;
        addBotMessage("No chatbot found. Please go back and crawl a website first.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bot_id: botId, question }),
        });

        showThinking(false);
        if (sendBtn) sendBtn.disabled = false;

        const data = await res.json();

        if (!res.ok) {
            addBotMessage(`⚠️ ${data.detail || "Error getting answer."}`);
            return;
        }

        addBotMessage(data.answer, data.sources || []);

    } catch {
        showThinking(false);
        if (sendBtn) sendBtn.disabled = false;
        addBotMessage("Cannot reach the server. Make sure the backend is running.");
    }
}


// ========================================
// MESSAGE BUILDERS
// ========================================

function addUserMessage(text) {
    const chat = document.getElementById("chat-window");
    if (!chat) return;
    const div = document.createElement("div");
    div.className = "message user-message";
    div.innerHTML = `
        <div class="bubble">${escapeHtml(text)}</div>
        <div class="timestamp">${getTime()}</div>
    `;
    chat.appendChild(div);
    scrollToBottom();
}

function addBotMessage(text, sources = []) {
    const chat = document.getElementById("chat-window");
    if (!chat) return;

    let sourcesHtml = "";
    if (sources.length > 0) {
        const links = sources.map(s => {
            try {
                return `<a href="${s}" target="_blank">${new URL(s).hostname}</a>`;
            } catch { return ""; }
        }).filter(Boolean).join(", ");
        sourcesHtml = `<div class="sources">Sources: ${links}</div>`;
    }

    const div = document.createElement("div");
    div.className = "message bot-message";
    div.innerHTML = `
        <div class="bubble">${formatMessage(text)}</div>
        ${sourcesHtml}
        <div class="timestamp">${getTime()}</div>
    `;
    chat.appendChild(div);
    scrollToBottom();
}


// ========================================
// FORMAT MESSAGE — converts plain text to HTML
// ========================================

function formatMessage(text) {
    // Escape HTML first for safety
    let safe = String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Convert **bold** or *bold*
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    safe = safe.replace(/\*(.*?)\*/g, "<strong>$1</strong>");

    // Convert bullet points starting with - or •
    safe = safe.replace(/^[-•]\s+(.+)$/gm, "<li>$1</li>");

    // Wrap consecutive <li> in <ul>
    safe = safe.replace(/(<li>.*?<\/li>\n?)+/gs, "<ul>$&</ul>");

    // Convert numbered lists 1. 2. 3.
    safe = safe.replace(/^\d+\.\s+(.+)$/gm, "<li>$1</li>");

    // Convert line breaks to <br>
    safe = safe.replace(/\n/g, "<br>");

    return safe;
}


// ========================================
// HELPERS
// ========================================

function showThinking(show) {
    document.getElementById("thinking")?.classList.toggle("hidden", !show);
}

function scrollToBottom() {
    const chat = document.getElementById("chat-window");
    if (chat) chat.scrollTop = chat.scrollHeight;
}

function getTime() {
    return new Date().toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit"
    });
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}