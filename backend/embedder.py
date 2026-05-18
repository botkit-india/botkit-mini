"""
embedder.py -- Day 2 & 3: Botkit Mini
--------------------------------------
Author  : Manav (Member 2)
Branch  : manav/dev

Day 3 Improvements:
- Added duplicate prevention: re-crawling same bot_id deletes and recreates collection
- Added comments explaining EphemeralClient limitation
- Added TODO for PersistentClient upgrade
"""

import chromadb
import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid
import sys

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50
EMBED_MODEL   = "nomic-embed-text"

# NOTE: EphemeralClient stores data IN MEMORY only.
# This means all embeddings are lost when the Python process exits.
# This is fine for Day 2/3 testing but NOT suitable for production.
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
    """
    Get or create a ChromaDB collection for a bot_id.
    NOTE: Does NOT clear existing data. Use _replace_collection() to prevent duplicates.
    """
    return chroma_client.get_or_create_collection(
        name=f"bot_{bot_id}",
        metadata={"hnsw:space": "cosine"},
    )


def _replace_collection(bot_id: str):
    """
    Delete the existing collection for this bot_id (if any) and create a fresh one.
    This prevents duplicate chunks when re-crawling the same website.
    """
    name = f"bot_{bot_id}"
    try:
        chroma_client.delete_collection(name=name)
        print(f"[embedder] Existing collection '{name}' deleted to prevent duplicates.")
    except Exception:
        pass  # Collection didn't exist yet -- that's fine
    return chroma_client.create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def _embed(text: str) -> list[float]:
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def embed_and_store(bot_id: str, pages: list[dict]) -> None:
    print(f"\n[embedder] Starting embed_and_store: bot_id={bot_id!r}")
    print(f"[embedder] Pages received: {len(pages)}")
    _check_ollama()

    # Use _replace_collection to prevent duplicate chunks on repeated runs
    collection = _replace_collection(bot_id)

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
        print(f"[embedder] Chunk count in ChromaDB: {collection.count()}")
    else:
        print("[embedder] No chunks generated.")


def retrieve(bot_id: str, question: str, top_k: int = 5) -> list[dict]:
    print(f"\n[embedder] Retrieving top {top_k} chunks for: {question!r}")
    _check_ollama()
    collection = _get_collection(bot_id)
    count = collection.count()
    if count == 0:
        print(f"[embedder] Warning: Collection bot_{bot_id} is empty.")
        return []
    question_vector = _embed(question)
    results = collection.query(
        query_embeddings=[question_vector],
        n_results=min(top_k, count),
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
    print("  EMBEDDER.PY -- Test Run (Day 3)")
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

    # Test 1 -- Store
    print("\n--- TEST 1: Store pages ---")
    try:
        embed_and_store(bot_id=BOT_ID, pages=fake_pages)
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    # Test 2 -- Retrieve
    print("\n--- TEST 2: Retrieve chunks ---")
    for q in ["How much is the Pro plan?", "Is data private?", "Who founded BotKit?"]:
        print(f"\nQ: {q}")
        for r in retrieve(BOT_ID, q, top_k=2):
            print(f"  [{r['distance']}] {r['source_url']}")
            print(f"  {r['text'][:120]}...")

    # Test 3 -- Empty page guard
    print("\n--- TEST 3: Empty page ---")
    embed_and_store(BOT_ID, [{"url": "https://example.com/empty", "text": ""}])

    # Test 4 -- Duplicate prevention: run embed_and_store again, chunk count should stay the same
    print("\n--- TEST 4: Duplicate prevention ---")
    print("Running embed_and_store a SECOND time with same data...")
    embed_and_store(bot_id=BOT_ID, pages=fake_pages)
    col = chroma_client.get_collection(f"bot_{BOT_ID}")
    count = col.count()
    print(f"Chunk count after second run: {count}")
    assert count == 3, f"Expected 3 chunks, got {count} -- duplicate prevention FAILED!"
    print("Duplicate prevention OK: chunk count stayed at 3, not 6.")

    print("\n" + "=" * 60)
    print("  All tests passed!")
    print("=" * 60)