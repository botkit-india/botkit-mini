BotKit India — Mini MVP
> Paste a URL. Get a working AI chatbot in minutes.
Built by a team of 3 — Chaitanya, Manav, Divyanshu.
---
What is this?
BotKit India is a mini MVP that lets you paste any website URL
and instantly get an AI chatbot trained on that website's content.
The bot answers questions based only on the website — no hallucinations,
no made-up answers.
Example:
Paste: `https://moderncoe.edu.in`
Ask: "What courses does this college offer?"
Bot answers from the actual website content
---
Tech Stack
Layer	Tool
Backend API	Python + FastAPI
Web Crawler	requests + BeautifulSoup + Playwright
Embeddings	Ollama nomic-embed-text (local, free)
Vector DB	ChromaDB (local, in-memory)
LLM	Groq API — llama-3.3-70b-versatile (free)
Frontend	Plain HTML + CSS + JS
Total cost: Rs.0 — everything runs free.
---
Prerequisites
Before running this project, install these on your machine:
Tool	Download	Purpose
Python 3.10+	python.org	Backend runtime
Ollama	ollama.com	Local embeddings
Git	git-scm.com	Version control
VS Code	code.visualstudio.com	Code editor
---
Setup Instructions
Follow these steps exactly. Any new team member should be
running the app in under 10 minutes.
Step 1 — Clone the repo
```bash
git clone https://github.com/botkit-india/botkit-mini.git
cd botkit-mini
```
Step 2 — Download the embedding model
```bash
ollama pull nomic-embed-text
```
Wait for it to finish (~250MB download).
Verify it worked:
```bash
ollama list
# Should show: nomic-embed-text
```
Step 3 — Create virtual environment
```bash
cd backend
python -m venv venv
```
Activate it:
Windows:
```bash
venv\Scripts\activate
```
Mac/Linux:
```bash
source venv/bin/activate
```
You should see `(venv)` in your terminal.
Step 4 — Install dependencies
```bash
pip install -r requirements.txt
pip install playwright
playwright install chromium
```
Step 5 — Create your .env file
Create a file called `.env` inside the `backend/` folder:
```
GROQ_API_KEY=your_groq_key_here
```
Get your free Groq API key at console.groq.com — takes 2 minutes,
no credit card needed.
⚠️ Never commit this file to GitHub. It's already in `.gitignore`.
Step 6 — Run the backend
```bash
uvicorn main:app --reload
```
You should see:
```
INFO: Uvicorn running on http://127.0.0.1:8000
INFO: Application startup complete.
```
Step 7 — Open the app
Go to:
```
http://localhost:8000/static/index.html
```
You should see the BotKit India homepage.
Step 8 — Test it
Paste any website URL — e.g. `https://books.toscrape.com`
Click Create Chatbot
Wait 1-2 minutes for crawl to complete
Click Start Chatting
Ask any question about the website
---
API Endpoints
The backend runs at `http://localhost:8000`.
Interactive docs available at `http://localhost:8000/docs`
Method	Endpoint	What it does
GET	`/`	Health check
POST	`/crawl`	Start crawling a website
GET	`/status/{bot_id}`	Check crawl status
POST	`/chat`	Ask a question
GET	`/bots`	List all active bots
POST /crawl
Request:
```json
{
  "url": "https://example.com"
}
```
Response:
```json
{
  "bot_id": "a1b2c3d4",
  "status": "crawling",
  "message": "Started crawling https://example.com"
}
```
GET /status/{bot_id}
Response:
```json
{
  "bot_id": "a1b2c3d4",
  "status": "ready",
  "pages_crawled": 12,
  "url": "https://example.com",
  "error": null
}
```
Status values:
`crawling` — still in progress
`ready` — bot is ready to chat
`error` — something went wrong
POST /chat
Request:
```json
{
  "bot_id": "a1b2c3d4",
  "question": "What does this company do?"
}
```
Response:
```json
{
  "bot_id": "a1b2c3d4",
  "question": "What does this company do?",
  "answer": "This company offers...",
  "sources": ["https://example.com/about"]
}
```
---
Project Structure
```
botkit-mini/
├── backend/
│   ├── main.py          ← FastAPI app — all API routes
│   ├── crawler.py       ← crawls website, extracts text
│   ├── embedder.py      ← chunks text, stores in ChromaDB
│   ├── chat.py          ← RAG pipeline + Groq API call
│   ├── requirements.txt ← all Python dependencies
│   ├── test_results.md  ← crawler test results
│   └── .env             ← your API keys (never commit this)
├── frontend/
│   ├── index.html       ← URL input page
│   ├── chat.html        ← chat interface page
│   ├── style.css        ← all styles
│   └── app.js           ← all JavaScript logic
├── .env.example         ← template for .env file
├── .gitignore
└── README.md
```
---
How It Works
```
User pastes URL
      ↓
POST /crawl → crawler.py visits all pages on the website
      ↓
embedder.py splits text into 500 word chunks
      ↓
Ollama converts each chunk to a vector embedding
      ↓
ChromaDB stores all vectors locally
      ↓
User asks a question
      ↓
POST /chat → question converted to vector
      ↓
ChromaDB finds top 7 most similar chunks
      ↓
Groq API (llama-3.3-70b) generates answer from chunks
      ↓
Answer displayed in chat UI
```
---
Team
Member	Role	Owns
Chaitanya	Backend Lead	main.py, chat.py, deployment
Manav	AI Lead	crawler.py, embedder.py, RAG quality
Divyanshu	Frontend Lead	index.html, chat.html, style.css, app.js
Daily workflow:
```bash
# Start of day — pull latest
git checkout yourname/dev
git fetch origin
git merge origin/main

# End of day — push to main
git checkout main
git pull origin main
git merge yourname/dev
git push origin main
git checkout yourname/dev
```
---
Known Limitations (Mini MVP)
ChromaDB is in-memory — all bots reset if server restarts
JS-heavy websites may crawl slowly (Playwright handles most cases)
No user authentication — anyone with the URL can use it
No persistent storage — not suitable for production yet
Runs on localhost only — not deployed to cloud yet
These are all fixed in the full product.
---
Troubleshooting
Problem: `ollama pull nomic-embed-text` fails
```bash
# Make sure Ollama is running
ollama serve
# Then retry the pull
```
Problem: `GROQ_API_KEY` not found
```
Make sure backend/.env exists with your real key
Make sure you're running uvicorn from inside the backend/ folder
```
Problem: 0 pages crawled
```
The website is JS-heavy. Playwright will handle it automatically
if installed. Run: pip install playwright && playwright install chromium
```
Problem: Merge conflict in Git
```bash
git merge --abort
git checkout --ours conflicted_file.py
git add .
git commit -m "resolve conflict"
```
Problem: Port 8000 already in use
```bash
# Run on a different port
uvicorn main:app --reload --port 8001
```
---
Next Steps — Full Product
After this mini MVP, the full product adds:
☁️ Cloud deployment (Render + Vercel)
🗄️ MongoDB Atlas for persistent storage + vector search
🔐 User authentication (JWT + Google OAuth)
💬 Embeddable widget (one line of JS)
📱 WhatsApp Business API bot
💳 Razorpay subscriptions (Rs.999/month)
🇮🇳 Hindi + 9 Indian languages via Sarvam AI
📊 Analytics dashboard
🔄 Auto re-crawl when website changes
---
Built with ❤️ in Pune, India — 2026
