"""
embedder.py

Turns crawled pages into searchable vector data.

Flow:
1. Take pages from crawler.py
2. Split each page into 500-word chunks with 50-word overlap
3. Convert each chunk into an embedding using Ollama
4. Store the chunks in a ChromaDB collection for one bot_id
5. Retrieve the most relevant chunks later for a user question
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

import chromadb
import ollama

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 5

_CHROMA_CLIENT: chromadb.ClientAPI | None = None


class EmbedderError(Exception):
    """Base exception for embedder-related problems."""


class OllamaUnavailableError(EmbedderError):
    """Raised when Ollama cannot generate embeddings."""


def get_chroma_client() -> chromadb.ClientAPI:
    """
    Return a single in-memory ChromaDB client for this Python process.

    This matches your Day 2 requirement of using ChromaDB locally in memory.
    """
    global _CHROMA_CLIENT

    if _CHROMA_CLIENT is None:
        _CHROMA_CLIENT = chromadb.Client()

    return _CHROMA_CLIENT


def _collection_name(bot_id: str) -> str:
    """Create a safe Chroma collection name from a bot_id."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", bot_id.strip())
    if not cleaned:
        raise ValueError("bot_id cannot be empty.")
    return f"bot_{cleaned}"


def _replace_collection(bot_id: str):
    """
    Create a fresh collection for one bot_id.

    If a collection already exists, we replace it gracefully so repeated runs
    do not create duplicate chunks.
    """
    client = get_chroma_client()
    name = _collection_name(bot_id)

    try:
        client.delete_collection(name=name)
        logger.info("Existing collection for bot_id '%s' was replaced.", bot_id)
    except Exception:
        pass

    return client.create_collection(name=name, metadata={"hnsw:space": "cosine"})


def get_or_create_collection(bot_id: str = "default"):
    """
    Compatibility helper for existing backend code.

    Day 2 code should prefer one collection per bot_id, but this keeps older
    imports working while you finish the rest of the project.
    """
    client = get_chroma_client()
    name = _collection_name(bot_id)
    try:
        return client.get_collection(name=name)
    except Exception:
        return client.create_collection(name=name, metadata={"hnsw:space": "cosine"})


def _get_collection(bot_id: str):
    """Return the collection for a bot_id if it exists."""
    client = get_chroma_client()
    return client.get_collection(name=_collection_name(bot_id))


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping word chunks.

    Example:
    - chunk 1 = words 0 to 499
    - chunk 2 = words 450 to 949

    We use words instead of characters because your Day 2 requirement is
    explicitly 500 words with 50-word overlap.
    """
    if not text or not text.strip():
        return []

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    step = chunk_size - chunk_overlap

    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        if not chunk_words:
            continue
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break

    return chunks


def _embed_text(text: str) -> list[float]:
    """
    Generate one embedding using Ollama.

    If Ollama is not running, we raise a friendly error that can be shown to
    the user instead of a raw stack trace.
    """
    try:
        if hasattr(ollama, "embed"):
            response = ollama.embed(model=EMBED_MODEL, input=text)
            embeddings = response.get("embeddings")
            if embeddings:
                return embeddings[0]
            if response.get("embedding"):
                return response["embedding"]

        response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
        return response["embedding"]
    except Exception as exc:
        raise OllamaUnavailableError(
            "Could not generate embeddings. Make sure Ollama is running and "
            f"the '{EMBED_MODEL}' model is installed."
        ) from exc


def _make_chunk_id(bot_id: str, url: str, chunk_index: int) -> str:
    """Create a stable ID for each stored chunk."""
    raw = f"{bot_id}:{url}:{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _embed_pages(bot_id: str, pages: list[dict[str, Any]], replace_existing: bool) -> dict[str, Any]:
    """Internal implementation shared by new and legacy call styles."""
    collection = _replace_collection(bot_id) if replace_existing else get_or_create_collection(bot_id)

    ids: list[str] = []
    documents: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict[str, Any]] = []

    total_pages = 0
    total_chunks = 0

    for page_index, page in enumerate(pages):
        url = str(page.get("url", "")).strip()
        text = str(page.get("text", "")).strip()
        title = str(page.get("title", "")).strip() or url

        if not url or not text:
            logger.warning("Skipping page %s because url or text is missing.", page_index)
            continue

        total_pages += 1
        chunks = chunk_text(text)
        logger.info("Page %s split into %s chunks.", url, len(chunks))

        for chunk_index, chunk in enumerate(chunks):
            embedding = _embed_text(chunk)

            ids.append(_make_chunk_id(bot_id, url, chunk_index))
            documents.append(chunk)
            embeddings.append(embedding)
            metadatas.append(
                {
                    "bot_id": bot_id,
                    "source_url": url,
                    "title": title,
                    "page_index": page_index,
                    "chunk_index": chunk_index,
                }
            )
            total_chunks += 1

    if not documents:
        raise ValueError("No valid page content was available to embed.")

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info(
        "Stored %s chunks from %s pages in collection %s.",
        total_chunks,
        total_pages,
        _collection_name(bot_id),
    )

    return {
        "status": "success",
        "bot_id": bot_id,
        "pages_processed": total_pages,
        "chunks_stored": total_chunks,
        "collection_name": _collection_name(bot_id),
    }


def embed_and_store(bot_id: str | dict[str, Any], pages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """
    Embed all crawled pages for one chatbot and store them in ChromaDB.

    Args:
        bot_id: Unique identifier for the chatbot
        pages: List of page dictionaries such as:
               [{"url": "...", "text": "..."}, {"url": "...", "text": "..."}]

    Returns:
        Summary dictionary with counts and status information
    """
    if isinstance(bot_id, dict):
        # Backward-compatible mode for the current FastAPI code:
        # embed_and_store(crawled_page_dict, force=False)
        return _embed_pages("default", [bot_id], replace_existing=False)

    if not bot_id or not bot_id.strip():
        raise ValueError("bot_id is required.")

    if not pages:
        raise ValueError("pages must contain at least one page.")

    return _embed_pages(bot_id, pages, replace_existing=True)


def retrieve(bot_id: str, question: str, top_k: int = TOP_K) -> list[dict[str, Any]]:
    """
    Retrieve the most relevant chunks for a user question.

    Args:
        bot_id: Which chatbot's data to search
        question: User question to embed and search for
        top_k: Number of matching chunks to return

    Returns:
        List of matches with chunk text and source URL
    """
    if not question or not question.strip():
        raise ValueError("question cannot be empty.")

    try:
        collection = _get_collection(bot_id)
    except Exception as exc:
        raise ValueError(
            f"No ChromaDB collection found for bot_id '{bot_id}'. "
            "Run embed_and_store() first."
        ) from exc

    query_embedding = _embed_text(question)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    matches: list[dict[str, Any]] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for document, metadata, distance in zip(documents, metadatas, distances):
        matches.append(
            {
                "chunk": document,
                "url": metadata.get("source_url", ""),
                "title": metadata.get("title", ""),
                "chunk_index": metadata.get("chunk_index", -1),
                "distance": distance,
            }
        )

    return matches


def search(query: str, n_results: int = 5, bot_id: str = "default") -> list[dict[str, Any]]:
    """
    Compatibility wrapper for existing chat.py code.

    New Day 2 code should call retrieve(bot_id, question, top_k).
    """
    matches = retrieve(bot_id, query, top_k=n_results)
    return [
        {
            "text": match["chunk"],
            "metadata": {
                "source_url": match["url"],
                "title": match["title"],
                "chunk_index": match["chunk_index"],
            },
            "distance": match["distance"],
            "relevance": round(1 - match["distance"], 4),
        }
        for match in matches
    ]


def get_stats(bot_id: str | None = None) -> dict[str, Any]:
    """
    Small helper for debugging or API status checks.

    If bot_id is provided, we return the chunk count for just that bot.
    """
    client = get_chroma_client()

    if bot_id:
        try:
            collection = _get_collection(bot_id)
            return {
                "bot_id": bot_id,
                "collection_name": _collection_name(bot_id),
                "total_chunks": collection.count(),
            }
        except Exception:
            return {
                "bot_id": bot_id,
                "collection_name": _collection_name(bot_id),
                "total_chunks": 0,
            }

    collections = client.list_collections()
    return {
        "total_collections": len(collections),
        "collections": [collection.name for collection in collections],
    }


if __name__ == "__main__":
    # Complete Day 2 test block:
    # 1. Store fake pages
    # 2. Ask a question
    # 3. Check whether the right chunk comes back
    sample_pages = [
        {
            "url": "https://example.com/python",
            "title": "Python Basics",
            "text": (
                "Python is a programming language used for web apps, automation, "
                "data analysis, and AI projects. Python has simple syntax and is "
                "popular for beginner-friendly development. "
            )
            * 40,
        },
        {
            "url": "https://example.com/chromadb",
            "title": "ChromaDB Notes",
            "text": (
                "ChromaDB is a vector database. It stores text chunks together with "
                "their embeddings so that we can retrieve similar content later. "
                "This is useful in retrieval augmented generation systems. "
            )
            * 40,
        },
    ]

    test_bot_id = "demo-bot"
    test_question = "Which database stores embeddings for retrieval?"

    try:
        print("Embedding sample pages...")
        store_result = embed_and_store(test_bot_id, sample_pages)
        print("Chunks stored successfully.")
        print(store_result)

        print("\nRetrieving relevant chunks...")
        retrieved = retrieve(test_bot_id, test_question, top_k=5)

        if not retrieved:
            print("No results found.")
        else:
            print("\nTop result:")
            print(f"URL: {retrieved[0]['url']}")
            print(f"Title: {retrieved[0]['title']}")
            print(f"Chunk index: {retrieved[0]['chunk_index']}")
            print(f"Text preview: {retrieved[0]['chunk'][:300]}...")

    except OllamaUnavailableError as exc:
        print(f"Ollama error: {exc}")
        print("Start Ollama first, then run: python embedder.py")
    except Exception as exc:
        print(f"Test failed: {exc}")
