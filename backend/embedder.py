"""
embedder.py — Day 2: Botkit Mini
---------------------------------
Author  : Manav (Member 2)
Branch  : manav/dev
"""

import chromadb
import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid
import sys

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50
EMBED_MODEL   = "nomic-embed-text"

chroma_client = chromadb.EphemeralClient()


def _check_ollama():
    try:
        ollama.embeddings(model=EMBED_MODEL, prompt="ping")
    except Exception:
        raise RuntimeError(
            "\n[ERROR] Cannot reach Ollama.\n"
            "  → Run: ollama serve\n"
            "  → Pull model: ollama pull nomic-embed-text\n"
        )


def _get_collection(bot_id: str):
    return chroma_client.get_or_create_collection(
        name=f"bot_{bot_id}",
        metadata={"hnsw:space": "cosine"},
    )


def _embed(text: str) -> list[float]:
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def embed_and_store(bot_id: str, pages: list[dict]) -> None:
    print(f"\n[embedder] Starting embed_and_store: bot_id={bot_id!r}")
    print(f"[embedder] Pages received: {len(pages)}")
    _check_ollama()
    collection = _get_collection(bot_id)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    all_embeddings, all_documents, all_metadatas, all_ids = [], [], [], []
    total_chunks = 0

    for page in pages:
        url  = page.get("url", "unknown")
        text = page.get("text", "")
        if not text.strip():
            print(f"[embedder]   Skipping empty page: {url}")
            continue
        chunks = splitter.split_text(text)
        print(f"[embedder]   {url} -> {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            all_embeddings.append(_embed(chunk))
            all_documents.append(chunk)
            all_metadatas.append({"source_url": url, "chunk_index": i, "bot_id": bot_id})
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
    else:
        print("[embedder] No chunks generated.")


def retrieve(bot_id: str, question: str, top_k: int = 5) -> list[dict]:
    print(f"\n[embedder] Retrieving top {top_k} chunks for: {question!r}")
    _check_ollama()
    collection = _get_collection(bot_id)
    question_vector = _embed(question)
    results = collection.query(
        query_embeddings=[question_vector],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    chunks    = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    formatted = [
        {"text": c, "source_url": m.get("source_url", ""), "distance": round(d, 4)}
        for c, m, d in zip(chunks, metadatas, distances)
    ]
    print(f"[embedder] Retrieved {len(formatted)} chunks")
    return formatted


if __name__ == "__main__":
    print("=" * 60)
    print("  EMBEDDER.PY — Test Run")
    print("=" * 60)

    fake_pages = [
        {
            "url": "https://example.com/about",
            "text": "We are BotKit, a company that builds AI chatbots. Founded 2023. Zero cloud dependencies.",
        },
        {
            "url": "https://example.com/pricing",
            "text": "BotKit offers three plans. Pro: $29/month, 5 chatbots, unlimited messages.",
        },
        {
            "url": "https://example.com/faq",
            "text": "Q: Is my data private? A: Yes, all on your machine. Q: Can I cancel? A: Yes, any time.",
        },
    ]

    BOT_ID = "test_bot_001"

    # Test 1 — Store
    print("\n--- TEST 1: Store pages ---")
    try:
        embed_and_store(bot_id=BOT_ID, pages=fake_pages)
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    # Test 2 — Retrieve
    print("\n--- TEST 2: Retrieve chunks ---")
    for q in ["How much is the Pro plan?", "Is data private?", "Who founded BotKit?"]:
        print(f"\nQ: {q}")
        for r in retrieve(BOT_ID, q, top_k=2):
            print(f"  [{r['distance']}] {r['source_url']}")
            print(f"  {r['text'][:120]}...")

    # Test 3 — Empty page guard
    print("\n--- TEST 3: Empty page ---")
    embed_and_store(BOT_ID, [{"url": "https://example.com/empty", "text": ""}])

    print("\n" + "=" * 60)
    print("  All tests passed!")
    print("=" * 60)