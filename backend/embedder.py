"""
embedder.py — Text → Vectors Pipeline for BotKit India
Chunks crawled text, generates embeddings via Ollama (nomic-embed-text),
and stores everything in ChromaDB for semantic search.
"""

import ollama
import chromadb
from chromadb.config import Settings
import hashlib
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chromadb_data")
CHUNK_SIZE = 500        # Target characters per chunk
CHUNK_OVERLAP = 100     # Overlap between chunks for context continuity
COLLECTION_NAME = "botkit_docs"


def get_chroma_client():
    """Initialize and return a persistent ChromaDB client."""
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client


def get_or_create_collection():
    """Get or create the ChromaDB collection for storing embeddings."""
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # Use cosine similarity
    )
    return collection


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks for embedding.
    
    Tries to split at sentence boundaries for cleaner chunks.
    Falls back to character-level splitting if sentences are too long.
    
    Args:
        text: The full text to chunk
        chunk_size: Target size per chunk in characters
        overlap: Overlap between consecutive chunks
        
    Returns:
        List of text chunks
    """
    if not text or len(text) < chunk_size:
        return [text] if text else []

    # Split into sentences first
    sentences = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Split on sentence-ending punctuation
        import re
        parts = re.split(r'(?<=[.!?])\s+', line)
        sentences.extend(parts)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # If adding this sentence exceeds chunk_size, save current and start new
        if len(current_chunk) + len(sentence) + 1 > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Keep overlap from the end of current chunk
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + " " + sentence
        else:
            current_chunk = current_chunk + " " + sentence if current_chunk else sentence

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    logger.info(f"📦 Split text into {len(chunks)} chunks (avg {sum(len(c) for c in chunks) // max(len(chunks), 1)} chars)")
    return chunks


def generate_embedding(text: str) -> list[float]:
    """
    Generate a 768-dimensional embedding vector using Ollama nomic-embed-text.
    
    Args:
        text: Text to embed
        
    Returns:
        List of 768 floats (the embedding vector)
    """
    try:
        result = ollama.embeddings(model=EMBED_MODEL, prompt=text)
        return result["embedding"]
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise


def generate_chunk_id(url: str, chunk_index: int) -> str:
    """Generate a deterministic unique ID for a chunk to avoid duplicates."""
    raw = f"{url}::chunk::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def is_url_already_embedded(url: str) -> bool:
    """Check if a URL has already been embedded in ChromaDB."""
    collection = get_or_create_collection()
    try:
        results = collection.get(
            where={"source_url": url},
            limit=1
        )
        return len(results["ids"]) > 0
    except Exception:
        return False


def embed_and_store(crawled_data: dict, force: bool = False) -> dict:
    """
    Main pipeline: chunk text → generate embeddings → store in ChromaDB.
    
    Args:
        crawled_data: Output from crawler.crawl() — dict with url, title, text, etc.
        force: If True, re-embed even if URL already exists
        
    Returns:
        Dictionary with status information
    """
    url = crawled_data["url"]
    title = crawled_data["title"]
    text = crawled_data["text"]

    # Check for duplicates
    if not force and is_url_already_embedded(url):
        logger.info(f"⏭️ Already embedded: {url}")
        return {
            "status": "skipped",
            "reason": "already_embedded",
            "url": url
        }

    # Step 1: Chunk the text
    chunks = chunk_text(text)
    if not chunks:
        return {
            "status": "error",
            "reason": "no_chunks_generated",
            "url": url
        }

    # Step 2: Generate embeddings for each chunk
    logger.info(f"🧠 Generating embeddings for {len(chunks)} chunks...")
    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        try:
            embedding = generate_embedding(chunk)
            chunk_id = generate_chunk_id(url, i)

            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk)
            metadatas.append({
                "source_url": url,
                "title": title,
                "domain": crawled_data.get("domain", ""),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "crawled_at": crawled_data.get("timestamp", ""),
            })
        except Exception as e:
            logger.error(f"Failed to embed chunk {i}: {e}")
            continue

    if not ids:
        return {
            "status": "error",
            "reason": "all_embeddings_failed",
            "url": url
        }

    # Step 3: Store in ChromaDB
    collection = get_or_create_collection()
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

    result = {
        "status": "success",
        "url": url,
        "title": title,
        "chunks_stored": len(ids),
        "total_chunks": len(chunks),
    }

    logger.info(f"✅ Stored {len(ids)} chunks for: {title}")
    return result


def search(query: str, n_results: int = 5) -> list[dict]:
    """
    Semantic search — find the most relevant chunks for a query.
    
    Args:
        query: The search query text
        n_results: Number of results to return
        
    Returns:
        List of dicts with document text, metadata, and distance score
    """
    collection = get_or_create_collection()

    # Generate embedding for the query
    query_embedding = generate_embedding(query)

    # Search ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    # Format results
    search_results = []
    for i in range(len(results["ids"][0])):
        search_results.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
            "relevance": round(1 - results["distances"][0][i], 4)
        })

    return search_results


def get_stats() -> dict:
    """Get statistics about the current ChromaDB collection."""
    try:
        collection = get_or_create_collection()
        count = collection.count()

        # Get unique URLs
        if count > 0:
            all_metadata = collection.get(include=["metadatas"])
            unique_urls = set()
            for meta in all_metadata["metadatas"]:
                if "source_url" in meta:
                    unique_urls.add(meta["source_url"])
            return {
                "total_chunks": count,
                "total_sources": len(unique_urls),
                "sources": list(unique_urls)
            }
        return {"total_chunks": 0, "total_sources": 0, "sources": []}
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"total_chunks": 0, "total_sources": 0, "sources": [], "error": str(e)}


if __name__ == "__main__":
    # Quick test — embed some sample text
    sample = {
        "url": "https://example.com/test",
        "title": "Test Document",
        "text": "This is a test document for BotKit India. " * 20,
        "domain": "example.com",
        "timestamp": "2026-05-16T00:00:00",
    }

    print("Embedding test document...")
    result = embed_and_store(sample)
    print(f"Result: {result}")

    print("\nSearching for 'test document'...")
    results = search("test document")
    for r in results:
        print(f"  [{r['relevance']}] {r['text'][:80]}...")
