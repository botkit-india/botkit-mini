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
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
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
    """Embed a single text string."""
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single Ollama call (much faster)."""
    if not texts:
        return []
    try:
        response = ollama.embed(model=EMBED_MODEL, input=texts)
        return response["embeddings"]
    except Exception:
        # Fallback: older Ollama versions don't support batch
        print("[embedder] Batch embed not supported, falling back to sequential...")
        return [_embed(t) for t in texts]


def _smart_chunk_size(num_pages: int) -> int:
    """Optimized chunk sizes — larger chunks = fewer Ollama calls = faster."""
    if num_pages < 10:
        return 500
    return 800


def _semantic_split(content: str, max_chunk_size: int = 800) -> list[str]:
    """
    Two-stage semantic chunking:
    1. Split by Markdown headers (keeps sections like ## Pricing intact)
    2. Only use RecursiveCharacterTextSplitter on chunks that are still too large
    
    This ensures structured content (tables, FAQ sections) stays in one chunk,
    while very long sections still get split reasonably.
    """
    # Stage 1: Split by markdown headers
    headers_to_split_on = [
        ("#", "heading_1"),
        ("##", "heading_2"),
        ("###", "heading_3"),
    ]
    
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,  # Keep headers in the chunk text for context
    )
    
    try:
        md_chunks = md_splitter.split_text(content)
    except Exception as e:
        print(f"[embedder] Markdown split failed ({e}), falling back to character split")
        # Fallback: treat entire content as one chunk for stage 2
        md_chunks = []
    
    # If markdown splitting produced nothing (e.g. plain text with no headers),
    # fall back to RecursiveCharacterTextSplitter on the whole content
    if not md_chunks:
        fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )
        return fallback_splitter.split_text(content)
    
    # Stage 2: Split any oversized header-based chunks with character splitter
    final_chunks = []
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk_size,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    
    for doc in md_chunks:
        chunk_text = doc.page_content
        # Prepend the header path as context (e.g. "Pricing > Plans")
        header_parts = [v for k, v in doc.metadata.items() if v]
        if header_parts:
            header_context = " > ".join(header_parts)
            chunk_text = f"Section: {header_context}\n{chunk_text}"
        
        if len(chunk_text) > max_chunk_size:
            # This section is too large — split it further
            sub_chunks = char_splitter.split_text(chunk_text)
            final_chunks.extend(sub_chunks)
        else:
            final_chunks.append(chunk_text)
    
    return final_chunks


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
    print(f"[embedder] Using chunk_size={chunk_size} (semantic + smart chunking)")

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

        # Use semantic splitting (markdown headers first, then character fallback)
        raw_chunks = _semantic_split(content, max_chunk_size=chunk_size)
        print(f"[embedder]   {url} -> {len(raw_chunks)} chunks")
        
        for i, chunk in enumerate(raw_chunks):
            # Prepend metadata context to chunk text
            meta_header = f"Page Title: {title}\n" if title else ""
            if description and i == 0:
                meta_header += f"Description: {description}\n"
            meta_header += f"URL: {url}\n\n"
            
            enriched_chunk = meta_header + chunk
            
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

    # Batch embed ALL chunks in a single Ollama call (massive speedup)
    if all_documents:
        print(f"[embedder] Batch-embedding {total_chunks} chunks...")
        all_embeddings = _embed_batch(all_documents)

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

    # Test 3 -- Empty page guard
    print("\n--- TEST 3: Empty page ---")
    embed_and_store(BOT_ID, [{"url": "https://example.com/empty", "text": "", "markdown": "", "title": "", "description": ""}])

    # Test 4 -- Duplicate prevention
    print("\n--- TEST 4: Duplicate prevention ---")
    embed_and_store(bot_id=BOT_ID, pages=fake_pages)
    col = chroma_client.get_collection(f"bot_{BOT_ID}")
    count = col.count()
    print(f"Chunk count after second run: {count}")
    assert count == 3, f"Expected 3 chunks, got {count} -- duplicate prevention FAILED!"
    print("Duplicate prevention OK: chunk count stayed at 3, not 6.")

    # Test 5 -- Smart chunking override
    print("\n--- TEST 5: Manual chunk_size override ---")
    embed_and_store(bot_id="override_test", pages=fake_pages, chunk_size=200)
    col2 = chroma_client.get_collection("bot_override_test")
    print(f"Override test chunk count: {col2.count()} (should be >= 3 with smaller chunks)")

    print("\n" + "=" * 60)
    print("  All tests passed!")
    print("=" * 60)