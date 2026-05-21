import uuid
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict
from dotenv import load_dotenv
from datetime import datetime

from crawler import crawl_website
from embedder import embed_and_store
from chat import answer_question

from database import create_indexes, bots_collection
from auth_routes import router as auth_router
from auth import get_current_user

load_dotenv(Path(__file__).parent / '.env')

app = FastAPI(title="BotKit India API", version="1.0.0")
# Include auth routes
app.include_router(auth_router)

# Create DB indexes on startup
@app.on_event("startup")
async def startup():
    create_indexes()
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
bot_info = {}


# ─── Request Models ───────────────────────────────────────────

class CrawlRequest(BaseModel):
    url: str

class ChatRequest(BaseModel):
    bot_id: str
    question: str
    history: Optional[List[Dict[str, str]]] = None
    language: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "BotKit India API is running!"}


@app.post("/crawl")
def crawl(req: CrawlRequest, current_user=Depends(get_current_user)):
    if not req.url.startswith("http"):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Must start with http or https."
        )

    bot_id = str(uuid.uuid4())[:8]
    bot_status[bot_id] = "crawling"
    bot_info[bot_id] = {
        "url": req.url,
        "pages_crawled": 0,
        "owner_id": current_user['sub']
    }

    def run_crawl():
        start_time = time.time()
        try:
            pages = crawl_website(req.url, max_pages=30)

            if time.time() - start_time > 300:
                bot_status[bot_id] = "error"
                bot_info[bot_id]["error"] = "Crawl timed out."
                return

            bot_info[bot_id]["pages_crawled"] = len(pages)

            if not pages:
                bot_status[bot_id] = "error"
                bot_info[bot_id]["error"] = "No pages crawled."
                return

            embed_and_store(bot_id, pages)
            bot_status[bot_id] = "ready"

            # Save to MongoDB
            bots_collection.insert_one({
                'bot_id': bot_id,
                'owner_id': current_user['sub'],
                'url': req.url,
                'pages_crawled': len(pages),
                'status': 'ready',
                'created_at': datetime.utcnow()
            })

            print(f"[main] Bot {bot_id} saved to MongoDB")

        except Exception as e:
            bot_status[bot_id] = "error"
            bot_info[bot_id]["error"] = str(e)
            print(f"[main] Bot {bot_id} failed: {e}")

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


@app.get("/bots")
def list_bots():
    """See all active bots and their status — for debugging"""
    return {
        "total": len(bot_status),
        "bots": [
            {
                "bot_id": bid,
                "status": bot_status[bid],
                "url": bot_info[bid].get("url", ""),
                "pages_crawled": bot_info[bid].get("pages_crawled", 0),
                "error": bot_info[bid].get("error", None)
            }
            for bid in bot_status
        ]
    }


@app.post("/chat")
def chat(req: ChatRequest, current_user=Depends(get_current_user)):
    if req.bot_id not in bot_status:
        raise HTTPException(
            status_code=404,
            detail="Bot not found. Please crawl your website again."
        )

    if bot_status[req.bot_id] != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Bot is not ready yet. Status: {bot_status[req.bot_id]}"
        )

    if not req.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    try:
        result = answer_question(req.bot_id, req.question, req.history, req.language)
        return {
            "bot_id": req.bot_id,
            "question": req.question,
            "answer": result["answer"],
            "sources": result["sources"],
            "language": result.get("language", "en")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating answer: {str(e)}"
        )


@app.get("/bots/mine")
def my_bots(current_user=Depends(get_current_user)):
    bots = list(bots_collection.find(
        {'owner_id': current_user['sub']},
        {'_id': 0}
    ))
    return {
        'total': len(bots),
        'bots': bots
    }