const API_URL = 'http://localhost:8000/api';

// --- Setup Page Logic ---
const crawlForm = document.getElementById('crawl-form');
if (crawlForm) {
    const urlInput = document.getElementById('url-input');
    const forceCrawl = document.getElementById('force-crawl');
    const submitBtn = document.getElementById('crawl-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');
    const statusMsg = document.getElementById('status-message');

    crawlForm.addEventListener('submit', async (e) => {
        e.submitter?.blur(); // removes focus from button
        e.preventDefault();
        
        const url = urlInput.value.trim();
        if (!url) return;

        // UI Loading State
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');
        statusMsg.classList.add('hidden');
        statusMsg.className = 'status-message';

        try {
            const response = await fetch(`${API_URL}/crawl`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    force: forceCrawl.checked
                })
            });

            const data = await response.json();

            statusMsg.classList.remove('hidden');
            if (response.ok) {
                statusMsg.classList.add('success');
                statusMsg.innerHTML = `<strong>Success!</strong> ${data.message}`;
                urlInput.value = ''; // clear on success
            } else {
                statusMsg.classList.add('error');
                statusMsg.textContent = data.detail || 'Failed to crawl URL.';
            }
        } catch (err) {
            statusMsg.classList.remove('hidden');
            statusMsg.classList.add('error');
            statusMsg.textContent = 'Network error. Make sure the backend is running.';
        } finally {
            // Restore UI
            submitBtn.disabled = false;
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
        }
    });
}

// --- Chat Page Logic ---
let chatHistory = [];

async function initChat() {
    updateStats();
    
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatHistoryDiv = document.getElementById('chat-history');
    const sendBtn = document.getElementById('send-btn');

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const question = chatInput.value.trim();
        if (!question) return;

        // 1. Add User Message to UI
        appendMessage('user', question);
        chatInput.value = '';
        
        // 2. Add Loading Indicator
        const typingId = addTypingIndicator();
        sendBtn.disabled = true;
        
        // Scroll to bottom
        chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;

        try {
            // 3. Call API
            const response = await fetch(`${API_URL}/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    history: chatHistory
                })
            });

            removeTypingIndicator(typingId);
            sendBtn.disabled = false;

            if (response.ok) {
                const data = await response.json();
                
                // Add to internal history for context in future turns
                chatHistory.push({ role: 'user', content: question });
                chatHistory.push({ role: 'assistant', content: data.answer });
                
                // Keep history reasonably sized
                if (chatHistory.length > 10) {
                    chatHistory = chatHistory.slice(chatHistory.length - 10);
                }

                // Append Bot Response
                appendMessage('system', data.answer, data.sources);
            } else {
                const errorData = await response.json();
                appendMessage('system', `**Error:** ${errorData.detail || 'Failed to get response.'}`);
            }
        } catch (err) {
            removeTypingIndicator(typingId);
            sendBtn.disabled = false;
            appendMessage('system', '**Network Error:** Could not connect to the backend server.');
        }
        
        chatHistoryDiv.scrollTop = chatHistoryDiv.scrollHeight;
        chatInput.focus();
    });
}

function appendMessage(sender, text, sources = []) {
    const chatHistoryDiv = document.getElementById('chat-history');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-msg fade-in`;
    
    const avatar = sender === 'user' ? '👤' : '🤖';
    
    // Convert markdown to HTML if marked is available, otherwise just text
    const htmlContent = typeof marked !== 'undefined' ? marked.parse(text) : `<p>${text}</p>`;

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        sourcesHtml = `<div class="sources-box">
            <h4>Sources:</h4>
            <ul>
                ${sources.map(s => `<li><a href="${s.url}" target="_blank" rel="noopener">${s.title}</a></li>`).join('')}
            </ul>
        </div>`;
    }

    msgDiv.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="bubble">
            ${htmlContent}
            ${sourcesHtml}
        </div>
    `;
    
    chatHistoryDiv.appendChild(msgDiv);
}

function addTypingIndicator() {
    const chatHistoryDiv = document.getElementById('chat-history');
    const id = 'typing-' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.className = `message system-msg fade-in`;
    msgDiv.id = id;
    
    msgDiv.innerHTML = `
        <div class="avatar">🤖</div>
        <div class="bubble" style="padding: 0.8rem 1.25rem;">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    
    chatHistoryDiv.appendChild(msgDiv);
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

async function updateStats() {
    try {
        const response = await fetch(`${API_URL}/status`);
        if (response.ok) {
            const data = await response.json();
            document.getElementById('stat-sources').textContent = data.stats.total_sources || 0;
            document.getElementById('stat-chunks').textContent = data.stats.total_chunks || 0;
        }
    } catch (e) {
        console.error("Failed to load stats", e);
    }
}
