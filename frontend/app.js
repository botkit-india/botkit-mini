// ========================================
// BotKit India — Frontend Logic
// ========================================

const API_BASE_URL = "http://localhost:8000";


// ========================================
// INDEX PAGE — CREATE CHATBOT
// ========================================

const createBotBtn = document.getElementById("createBotBtn");

if (createBotBtn) {

    createBotBtn.addEventListener("click", () => {
        createChatbot(document.getElementById("websiteUrl").value.trim());
    });

    document.getElementById("websiteUrl")?.addEventListener("keypress", (e) => {
        if (e.key === "Enter") createChatbot(e.target.value.trim());
    });

}


async function createChatbot(url) {

    if (!url) {
        shakeInput();
        return;
    }

    const bot_id = "test_bot_001";
    localStorage.setItem("website_url", url);
    localStorage.setItem("bot_id", bot_id);

    // --- UI refs ---
    const layout         = document.getElementById("appLayout");
    const urlForm        = document.getElementById("urlForm");
    const crawlingStatus = document.getElementById("crawlingStatus");
    const progressTrack  = document.getElementById("progressTrack");
    const progressBar    = document.getElementById("progressBar");
    const statusText     = document.getElementById("statusText");
    const crawlCount     = document.getElementById("crawlCount");
    const errorMsg       = document.getElementById("errorMsg");
    const chatLink       = document.getElementById("chatLink");
    const resultsPanel   = document.getElementById("resultsPanel");
    const pagesBadge     = document.getElementById("pagesBadge");
    const pagesList      = document.getElementById("pagesList");

    // --- Show loading state ---
    createBotBtn.disabled = true;
    urlForm.querySelector("input").disabled = true;
    crawlingStatus.classList.remove("hidden");
    progressTrack.classList.remove("hidden");
    errorMsg.classList.add("hidden");

    // --- Animate progress bar while waiting ---
    const stages = [
        { text: "Crawling your website…",   progress: 20 },
        { text: "Extracting content…",       progress: 45 },
        { text: "Processing pages…",         progress: 70 },
        { text: "Wrapping up…",              progress: 90 },
    ];

    let count = 0;
    let stageIdx = 0;
    statusText.textContent = stages[0].text;
    progressBar.style.width = stages[0].progress + "%";

    const ticker = setInterval(() => {
        count++;
        crawlCount.textContent = `Pages found: ${count}`;
        if (count % 2 === 0 && stageIdx < stages.length - 1) {
            stageIdx++;
            statusText.textContent = stages[stageIdx].text;
            progressBar.style.width = stages[stageIdx].progress + "%";
        }
    }, 500);

    try {

        const res = await fetch(`${API_BASE_URL}/crawl`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url, bot_id }),
        });

        clearInterval(ticker);

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Crawl failed.");
        }

        const data = await res.json();

        // --- Finish progress bar ---
        statusText.textContent = "Done!";
        progressBar.style.width = "100%";
        crawlCount.textContent = `Pages crawled: ${data.pages_crawled}`;

        // --- Short pause then trigger split layout ---
        await sleep(500);

        // Transition: centered → split
        layout.classList.remove("state-centered");
        layout.classList.add("state-split");
        resultsPanel.classList.remove("hidden");

        // Hide crawling status; show chat link
        crawlingStatus.classList.add("hidden");
        progressTrack.classList.add("hidden");
        chatLink.classList.remove("hidden");

        // Update results panel header
        pagesBadge.textContent = `${data.pages_crawled} page${data.pages_crawled !== 1 ? "s" : ""}`;

        // --- Populate page cards ---
        pagesList.innerHTML = "";
        const previews = data.pages_preview || [];

        if (previews.length === 0) {
            pagesList.innerHTML = `<p style="font-size:0.82rem;color:var(--grey-500);">No page previews available.</p>`;
        } else {
            previews.forEach((page, i) => {
                const card = document.createElement("div");
                card.className = "page-card";
                card.style.animationDelay = `${i * 0.05}s`;
                card.innerHTML = `
                    <div class="page-card-url">${escapeHtml(page.url)}</div>
                    <div class="page-card-preview">${escapeHtml(page.preview)}</div>
                `;
                pagesList.appendChild(card);
            });
        }

    } catch (err) {
        clearInterval(ticker);
        crawlingStatus.classList.add("hidden");
        progressTrack.classList.add("hidden");
        createBotBtn.disabled = false;
        urlForm.querySelector("input").disabled = false;
        errorMsg.textContent = `⚠️ ${err.message}`;
        errorMsg.classList.remove("hidden");
    }

}


function shakeInput() {
    const input = document.getElementById("websiteUrl");
    if (!input) return;
    input.style.borderColor = "#f87171";
    setTimeout(() => { input.style.borderColor = ""; }, 2000);
    input.focus();
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


// ========================================
// CHAT PAGE — MESSAGING
// ========================================

const sendBtn      = document.getElementById("sendBtn");
const messageInput = document.getElementById("messageInput");
const clearChatBtn = document.getElementById("clearChatBtn");

if (sendBtn)      sendBtn.addEventListener("click", sendMessage);
if (messageInput) messageInput.addEventListener("keypress", e => {
    if (e.key === "Enter") sendMessage();
});

document.querySelectorAll(".suggestion-chip").forEach(chip => {
    chip.addEventListener("click", () => {
        const msg = chip.getAttribute("data-msg");
        if (msg && messageInput) {
            messageInput.value = msg;
            document.getElementById("suggestions")?.remove();
            sendMessage();
        }
    });
});

if (clearChatBtn) {
    clearChatBtn.addEventListener("click", () => {
        if (confirm("Clear conversation?")) location.reload();
    });
}


// ========================================
// SEND MESSAGE
// ========================================

const fakeResponses = [
    "Our pricing starts at ₹999/month for the Starter plan.",
    "You can train your chatbot using your website URL and uploaded PDFs.",
    "BotKit supports Hindi and English out of the box.",
    "You can deploy your chatbot on WhatsApp, your website, and more.",
    "Your chatbot can answer customer questions 24/7.",
    "The dashboard includes analytics and full conversation history.",
    "BotKit uses RAG (Retrieval-Augmented Generation) for accurate answers.",
];

async function sendMessage() {

    const input         = document.getElementById("messageInput");
    const chatWindow    = document.getElementById("chatWindow");
    const thinking      = document.getElementById("thinkingIndicator");
    const thinkingLabel = document.getElementById("thinkingLabel");

    const question = input.value.trim();
    if (!question) return;

    const bot_id = localStorage.getItem("bot_id") || "test_bot_001";
    const time   = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    // User bubble
    const userRow = document.createElement("div");
    userRow.className = "message-row user";
    userRow.innerHTML = `
        <div class="avatar">🧑</div>
        <div class="message-bubble user-bubble">
            ${escapeHtml(question)}
            <span class="timestamp">${time}</span>
        </div>
    `;
    chatWindow.insertBefore(userRow, thinking);
    input.value = "";
    chatWindow.scrollTop = chatWindow.scrollHeight;
    document.getElementById("suggestions")?.remove();

    // Show thinking
    thinking.classList.remove("hidden");
    if (thinkingLabel) thinkingLabel.classList.remove("hidden");
    chatWindow.scrollTop = chatWindow.scrollHeight;

    try {
        const res = await fetch(`${API_BASE_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bot_id, question }),
        });

        thinking.classList.add("hidden");
        if (thinkingLabel) thinkingLabel.classList.add("hidden");

        let replyText;
        if (!res.ok) {
            // Backend not ready yet — fall back to fake response
            replyText = fakeResponses[Math.floor(Math.random() * fakeResponses.length)];
        } else {
            const data = await res.json();
            replyText = data.answer;
        }

        const botRow = document.createElement("div");
        botRow.className = "message-row bot";
        botRow.innerHTML = `
            <div class="avatar">🤖</div>
            <div class="message-bubble bot-bubble">
                ${escapeHtml(replyText)}
                <span class="timestamp">${time}</span>
            </div>
        `;
        chatWindow.insertBefore(botRow, thinking);
        chatWindow.scrollTop = chatWindow.scrollHeight;

    } catch {
        // Network error — fall back to fake response
        thinking.classList.add("hidden");
        if (thinkingLabel) thinkingLabel.classList.add("hidden");

        const fallback = fakeResponses[Math.floor(Math.random() * fakeResponses.length)];
        const botRow = document.createElement("div");
        botRow.className = "message-row bot";
        botRow.innerHTML = `
            <div class="avatar">🤖</div>
            <div class="message-bubble bot-bubble">
                ${escapeHtml(fallback)}
                <span class="timestamp">${time}</span>
            </div>
        `;
        chatWindow.insertBefore(botRow, thinking);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

}


// ========================================
// UTILS
// ========================================

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}