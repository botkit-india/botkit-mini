import uuid
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from crawler import crawl_website
from embedder import embed_and_store
from chat import answer_question

load_dotenv(Path(__file__).parent / '.env')

app = FastAPI(title="BotKit India API", version="1.0.0")

# Allow frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend folder so you can open it via localhost:8000/static/
app.mount(
    "/static",
    StaticFiles(directory="../frontend"),
    name="static"
)

# In-memory status tracker
# { bot_id: "crawling" | "ready" | "error" }
bot_status = {}
bot_info = {}  # stores extra info like pages crawled


# ─── Request Models ───────────────────────────────────────────

class CrawlRequest(BaseModel):
    url: str

class ChatRequest(BaseModel):
    bot_id: str
    question: str


# ─── Endpoints ────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "BotKit India API is running!"}


@app.post("/crawl")
def crawl(req: CrawlRequest):
    """
    Accepts a URL, starts crawling in background.
    Returns bot_id immediately — frontend polls /status to check progress.
    """
    if not req.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL. Must start with http or https.")

    bot_id = str(uuid.uuid4())[:8]
    bot_status[bot_id] = "crawling"
    bot_info[bot_id] = {"url": req.url, "pages_crawled": 0}

    def run_crawl():
        try:
            pages = crawl_website(req.url, max_pages=30)
            bot_info[bot_id]["pages_crawled"] = len(pages)

            if not pages:
                bot_status[bot_id] = "error"
                bot_info[bot_id]["error"] = "No pages could be crawled from this URL."
                return

            embed_and_store(bot_id, pages)
            bot_status[bot_id] = "ready"
            print(f"[main] Bot {bot_id} ready — {len(pages)} pages crawled")

        except Exception as e:
            bot_status[bot_id] = "error"
            bot_info[bot_id]["error"] = str(e)
            print(f"[main] Bot {bot_id} failed: {e}")

    # Run crawl in background so API returns immediately
    threading.Thread(target=run_crawl, daemon=True).start()

    return {
        "bot_id": bot_id,
        "status": "crawling",
        "message": f"Started crawling {req.url}"
    }


@app.get("/status/{bot_id}")
def status(bot_id: str):
    """
    Check if a bot is ready to chat.
    Frontend polls this every 2 seconds after calling /crawl.
    """
    if bot_id not in bot_status:
        raise HTTPException(status_code=404, detail="Bot not found.")

    return {
        "bot_id": bot_id,
        "status": bot_status[bot_id],
        "pages_crawled": bot_info[bot_id].get("pages_crawled", 0),
        "url": bot_info[bot_id].get("url", ""),
        "error": bot_info[bot_id].get("error", None)
    }


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Accepts bot_id + question, returns answer from Groq
    based only on the crawled website content.
    """
    if req.bot_id not in bot_status:
        raise HTTPException(status_code=404, detail="Bot not found. Please crawl a website first.")

    if bot_status[req.bot_id] != "ready":
        raise HTTPException(status_code=400, detail=f"Bot is not ready yet. Current status: {bot_status[req.bot_id]}")

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = answer_question(req.bot_id, req.question)
        return {
            "bot_id": req.bot_id,
            "question": req.question,
            "answer": result["answer"],
            "sources": result["sources"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")