"""
main.py — FastAPI Backend for BotKit India
Provides REST API endpoints for crawling URLs, querying the RAG bot,
and checking system status.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from crawler import crawl
from embedder import embed_and_store, search, get_stats
from chat import chat

# ─── FastAPI App ─────────────────────────────────────────
app = FastAPI(
    title="BotKit India API",
    description="Paste a URL → Get a chatbot. RAG-powered by Ollama + Groq.",
    version="1.0.0",
)

# CORS — allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response Models ───────────────────────────

class CrawlRequest(BaseModel):
    url: str
    force: bool = False  # Force re-crawl even if already embedded

class QueryRequest(BaseModel):
    question: str
    history: list[dict] | None = None  # Optional conversation history

class CrawlResponse(BaseModel):
    status: str
    url: str
    title: str | None = None
    chunks_stored: int | None = None
    message: str

class QueryResponse(BaseModel):
    answer: str
    sources: list[dict] = []
    usage: dict | None = None
    model: str | None = None


# ─── API Endpoints ───────────────────────────────────────

@app.post("/api/crawl", response_model=CrawlResponse)
async def crawl_url(request: CrawlRequest):
    """
    Crawl a URL — fetch content, chunk it, embed it, store in ChromaDB.
    """
    logger.info(f"📥 Crawl request: {request.url}")

    # Step 1: Crawl the page
    crawled = crawl(request.url)
    if not crawled:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to crawl URL: {request.url}. Check if the URL is valid and accessible."
        )

    # Step 2: Embed and store
    try:
        result = embed_and_store(crawled, force=request.force)
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embeddings. Is Ollama running? Error: {str(e)}"
        )

    if result["status"] == "skipped":
        return CrawlResponse(
            status="skipped",
            url=request.url,
            title=crawled["title"],
            chunks_stored=0,
            message=f"Already embedded. Use force=true to re-crawl."
        )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=f"Embedding error: {result.get('reason', 'unknown')}")

    return CrawlResponse(
        status="success",
        url=request.url,
        title=result.get("title", ""),
        chunks_stored=result.get("chunks_stored", 0),
        message=f"Successfully crawled and stored {result.get('chunks_stored', 0)} chunks."
    )


@app.post("/api/query", response_model=QueryResponse)
async def query_bot(request: QueryRequest):
    """
    Ask a question — retrieves relevant context and generates an answer.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    logger.info(f"❓ Query: {request.question}")

    try:
        result = chat(request.question, request.history)
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

    return QueryResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        usage=result.get("usage"),
        model=result.get("model"),
    )


@app.get("/api/status")
async def get_status():
    """
    Health check — returns system status and stats.
    """
    stats = get_stats()

    # Check Ollama
    ollama_ok = False
    try:
        import ollama as ollama_client
        ollama_client.list()
        ollama_ok = True
    except Exception:
        pass

    # Check Groq key
    groq_key = os.getenv("GROQ_API_KEY", "")
    groq_configured = bool(groq_key) and groq_key != "your_groq_key_here"

    return {
        "status": "online",
        "services": {
            "ollama": "connected" if ollama_ok else "disconnected",
            "groq": "configured" if groq_configured else "not_configured",
            "chromadb": "active",
        },
        "stats": stats,
    }


@app.delete("/api/sources/{url:path}")
async def delete_source(url: str):
    """Delete all chunks for a specific source URL from ChromaDB."""
    try:
        from embedder import get_or_create_collection
        collection = get_or_create_collection()
        
        # Get IDs for this URL
        results = collection.get(where={"source_url": url})
        if not results["ids"]:
            raise HTTPException(status_code=404, detail=f"No data found for URL: {url}")
        
        collection.delete(ids=results["ids"])
        return {
            "status": "deleted",
            "url": url,
            "chunks_removed": len(results["ids"])
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Serve Frontend ─────────────────────────────────────

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/chat")
    async def serve_chat():
        return FileResponse(os.path.join(frontend_dir, "chat.html"))


# ─── Run ─────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
