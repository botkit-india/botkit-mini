"""
embedder.py -- Day 2, 3, 4+5, and Day 6 Upgrades: Botkit Mini
-----------------------------------------------------------
Author  : Manav (Member 2)
Branch  : manav/dev

Upgrades:
- Prepend page title/description/URL to every chunk (context enrichment)
- Use markdown if crawled (maintains layout structure)
- Hybrid search (Cosine Vector Similarity + local exact-match keyword boosting)
- Retrieve-then-Rerank (Rerank top 20 candidates down to top_k)
"""

import chromadb
import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid
import sys
import re

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50
EMBED_MODEL   = "nomic-embed-text"

# NOTE: EphemeralClient stores data IN MEMORY only.
# TODO: Switch to PersistentClient for full product:
#   chromadb.PersistentClient(path="./chromadb_data")
chroma_client = chromadb.EphemeralClient()


def _check_ollama():
    try:
        ollama.embeddings(model=EMBED_MODEL, prompt="ping")
    except Exception:
        raise RuntimeError(
            "\n[ERROR] Cannot reach Ollama.\n"
            "  -> Run: ollama serve\n"
            "  -> Pull model: ollama pull nomic-embed-text\n"
        )


def _get_collection(bot_id: str):
    """Get or create a ChromaDB collection for a bot_id."""
    return chroma_client.get_or_create_collection(
        name=f"bot_{bot_id}",
        metadata={"hnsw:space": "cosine"},
    )


def _replace_collection(bot_id: str):
    """Delete the existing collection for this bot_id and create a fresh one."""
    name = f"bot_{bot_id}"
    try:
        chroma_client.delete_collection(name=name)
        print(f"[embedder] Existing collection '{name}' deleted to prevent duplicates.")
    except Exception:
        pass  # Collection didn't exist yet
    return chroma_client.create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def _embed(text: str) -> list[float]:
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def _smart_chunk_size(num_pages: int) -> int:
    """Smaller chunks for small sites, larger chunks for bigger sites."""
    if num_pages < 10:
        return 300
    return 500


def hybrid_rerank(chunks_list: list[dict], query: str) -> list[dict]:
    """
    Day 6 Upgrade: Hybrid reranking (BM25-style keyword and phrase boosting)
    Decreases distance score (cosine distance: lower is better) for documents that 
    contain exact keyword or multi-word matches from the query.
    """
    stopwords = {'what', 'how', 'where', 'why', 'is', 'the', 'a', 'of', 'in', 'to', 'for', 'on', 'with', 'at', 'by', 'an', 'and', 'or', 'does', 'do', 'any', 'about'}
    query_clean = re.sub(r'[^\w\s]', '', query.lower())
    query_words = [w for w in query_clean.split() if w not in stopwords and len(w) > 2]
    
    # Extract 2-word phrases for exact sequence matching (e.g. "Sharp Objects")
    phrases = []
    words_raw = [w for w in query_clean.split() if len(w) > 2]
    for i in range(len(words_raw) - 1):
        phrases.append(f"{words_raw[i]} {words_raw[i+1]}")
        
    for r in chunks_list:
        text_lower = r["text"].lower()
        boost = 0.0
        
        # 1. Exact phrase matches (highest boost)
        for phrase in phrases:
            if phrase in text_lower:
                boost += 0.25
                
        # 2. Individual keyword matches
        matched_words = 0
        for word in query_words:
            if word in text_lower:
                boost += 0.06
                matched_words += 1
                
        # All query keywords match bonus
        if query_words and matched_words == len(query_words):
            boost += 0.10
            
        r["original_distance"] = r["distance"]
        r["distance"] = max(0.0, r["distance"] - boost)
        
    # Re-sort chunks so the best boosted ones are first
    chunks_list.sort(key=lambda x: x["distance"])
    return chunks_list


def embed_and_store(bot_id: str, pages: list[dict], chunk_size: int = None) -> None:
    """
    Embed all crawled pages and store in ChromaDB.
    Enriches chunks with page titles, descriptions, and source URLs.
    """
    print(f"\n[embedder] Starting embed_and_store: bot_id={bot_id!r}")
    print(f"[embedder] Pages received: {len(pages)}")
    _check_ollama()

    collection = _replace_collection(bot_id)

    if chunk_size is None:
        chunk_size = _smart_chunk_size(len(pages))
    print(f"[embedder] Using chunk_size={chunk_size} (smart chunking)")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    all_embeddings, all_documents, all_metadatas, all_ids = [], [], [], []
    total_chunks = 0

    for page in pages:
        url = page.get("url", "unknown")
        # Prioritize markdown to keep HTML formatting/structure intact
        content = page.get("markdown", "")
        if not content.strip():
            content = page.get("text", "")
            
        title = page.get("title", "")
        description = page.get("description", "")

        if not content.strip():
            print(f"[embedder]   Skipping empty page: {url}")
            continue

        raw_chunks = splitter.split_text(content)
        print(f"[embedder]   {url} -> {len(raw_chunks)} chunks")
        
        for i, chunk in enumerate(raw_chunks):
            # Prepend metadata context to chunk text
            meta_header = f"Page Title: {title}\n" if title else ""
            if description and i == 0:
                meta_header += f"Description: {description}\n"
            meta_header += f"URL: {url}\n\n"
            
            enriched_chunk = meta_header + chunk
            
            all_embeddings.append(_embed(enriched_chunk))
            all_documents.append(enriched_chunk)
            all_metadatas.append({
                "source_url": url, 
                "chunk_index": i, 
                "bot_id": bot_id,
                "title": title,
                "description": description
            })
            all_ids.append(str(uuid.uuid4()))
            total_chunks += 1

    if all_ids:
        collection.add(
            embeddings=all_embeddings,
            documents=all_documents,
            metadatas=all_metadatas,
            ids=all_ids,
        )
        print(f"\n[embedder] Stored {total_chunks} chunks (collection: bot_{bot_id})")
        print(f"[embedder] Chunk count in ChromaDB: {collection.count()}")
    else:
        print("[embedder] No chunks generated.")


def retrieve(bot_id: str, question: str, top_k: int = 7) -> list[dict]:
    """
    Retrieve candidate chunks, apply hybrid reranking, and return top_k results.
    """
    print(f"\n[embedder] Retrieving top {top_k} chunks for: {question!r}")
    _check_ollama()
    collection = _get_collection(bot_id)
    count = collection.count()
    if count == 0:
        print(f"[embedder] Warning: Collection bot_{bot_id} is empty.")
        return []
        
    question_vector = _embed(question)
    
    # Retrieve top 20 candidate chunks for re-ranking
    candidate_k = min(20, count)
    results = collection.query(
        query_embeddings=[question_vector],
        n_results=candidate_k,
        include=["documents", "metadatas", "distances"],
    )
    
    chunks    = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    
    formatted = [
        {
            "text": c, 
            "source_url": m.get("source_url", ""), 
            "distance": round(d, 4),
            "title": m.get("title", ""),
            "description": m.get("description", "")
        }
        for c, m, d in zip(chunks, metadatas, distances)
    ]
    
    # Perform hybrid re-ranking
    reranked = hybrid_rerank(formatted, question)
    final_results = reranked[:top_k]
    
    print(f"[embedder] Retrieved {len(final_results)} chunks (reranked from {candidate_k})")
    return final_results


if __name__ == "__main__":
    print("=" * 60)
    print("  EMBEDDER.PY -- Upgraded Test Run")
    print("=" * 60)

    fake_pages = [
        {
            "url": "https://example.com/about",
            "title": "About Us | BotKit",
            "description": "Information about BotKit company profile.",
            "text": "We are BotKit, a company that builds AI chatbots. Founded 2023. Zero cloud dependencies.",
            "markdown": "# About Us\nWe are BotKit, a company that builds AI chatbots. Founded 2023. Zero cloud dependencies."
        },
        {
            "url": "https://example.com/pricing",
            "title": "Pricing & Plans | BotKit",
            "description": "View pricing details for BotKit chatbot plans.",
            "text": "BotKit offers three plans. Pro: $29/month, 5 chatbots, unlimited messages.",
            "markdown": "# Pricing\nBotKit offers three plans. Pro: $29/month, 5 chatbots, unlimited messages."
        },
        {
            "url": "https://example.com/faq",
            "title": "FAQ | BotKit Support",
            "description": "Frequently asked questions about BotKit privacy.",
            "text": "Q: Is my data private? A: Yes, all on your machine. Q: Can I cancel? A: Yes, any time.",
            "markdown": "# FAQ\nQ: Is my data private? A: Yes, all on your machine.\nQ: Can I cancel? A: Yes, any time."
        },
    ]

    BOT_ID = "test_bot_001"

    # Test 1 -- Store
    print("\n--- TEST 1: Store pages ---")
    try:
        embed_and_store(bot_id=BOT_ID, pages=fake_pages)
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    # Test 2 -- Retrieve and check hybrid boost for "pricing"
    print("\n--- TEST 2: Retrieve chunks (top_k=7) ---")
    for q in ["How much is the Pro plan?", "Is data private?", "Who founded BotKit?"]:
        print(f"\nQ: {q}")
        for r in retrieve(BOT_ID, q, top_k=3):
            print(f"  [{r['distance']}] {r['source_url']}")
            print(f"  {r['text'][:120]}...")

    # Test 3 -- Duplicate prevention
    print("\n--- TEST 3: Duplicate prevention ---")
    embed_and_store(bot_id=BOT_ID, pages=fake_pages)
    col = chroma_client.get_collection(f"bot_{BOT_ID}")
    count = col.count()
    print(f"Chunk count: {count}")
    assert count == 3, f"Expected 3 chunks, got {count}"
    print("Duplicate prevention OK.")

    print("\n" + "=" * 60)
    print("  All tests passed!")
    print("=" * 60)