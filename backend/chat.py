import os
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path
from embedder import retrieve

# Load .env file to get GROQ_API_KEY
load_dotenv(Path(__file__).parent / '.env')

# Initialize Groq client
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

def answer_question(bot_id, question):
    """
    Main RAG function.
    Takes a bot_id and question, returns an answer from Groq
    based only on the website content stored in ChromaDB.
    """

    # Step 1 — Retrieve top 5 relevant chunks from ChromaDB
    print(f"\nSearching ChromaDB for: '{question}'")
    results = retrieve(bot_id, question, top_k=5)

    if not results:
        return {
            'answer': "I don't have any information about that website yet. Please crawl a website first.",
            'sources': []
        }

    # Step 2 — Build context from retrieved chunks
    context = '\n---\n'.join([r['text'] for r in results])

    # Step 3 — Get unique source URLs
    sources = list(set(r['source_url'] for r in results))
    print(f"Found {len(results)} relevant chunks from {len(sources)} pages")

    # Step 4 — Build the prompt
    prompt = f"""You are a helpful AI assistant for a website.
Answer based ONLY on the context below.
Format your answer clearly:
- Use bullet points for lists
- Use short paragraphs for explanations
- Bold important words using *word*
- Keep answers concise and easy to read
If the answer is not in the context say:
"I couldn't find that information on this website. 
You can try contacting them directly for more details."
Never make up information. Never use outside knowledge.

Context:
{context}

Question: {question}

Answer:"""

    # Step 5 — Call Groq API
    print("Calling Groq API...")
    response = groq_client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ],
        max_tokens=500,
        temperature=0.1
    )

    answer = response.choices[0].message.content.strip()
    print(f"Answer received: {answer[:100]}...")

    return {
        'answer': answer,
        'sources': sources
    }


# ---- TEST BLOCK ----
if __name__ == "__main__":
    from crawler import crawl_website
    from embedder import embed_and_store

    print("=== FULL RAG PIPELINE TEST ===\n")

    # Step 1 — Crawl a website
    print("Step 1: Crawling website...")
    test_url = "https://books.toscrape.com"
    pages = crawl_website(test_url, max_pages=5)
    print(f"Crawled {len(pages)} pages\n")

    # Step 2 — Embed and store in ChromaDB
    print("Step 2: Embedding and storing in ChromaDB...")
    bot_id = "test_bot_001"
    embed_and_store(bot_id, pages)
    print("Stored successfully\n")

    # Step 3 — Ask questions
    print("Step 3: Asking questions...\n")

    questions = [
        "What kind of books are available?",
        "What categories exist on this website?",
        "What is the price of books?",
        "Do you sell electronics?"
    ]

    for q in questions:
        print(f"Q: {q}")
        result = answer_question(bot_id, q)
        print(f"A: {result['answer']}")
        print(f"Sources: {result['sources']}")
        print("-" * 50)