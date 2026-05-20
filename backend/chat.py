import os
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path
from embedder import retrieve

# Load .env file to get GROQ_API_KEY
load_dotenv(Path(__file__).parent / '.env')

# Initialize Groq client
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))


def rewrite_query(question, chat_history):
    """
    Use LLM to rewrite user question with context of chat history 
    so it becomes a standalone query that ChromaDB can search for.
    """
    if not chat_history:
        return question

    print(f"[chat] Rewriting query using chat history...")
    
    # Format last 4 turns for context
    history_str = ""
    for msg in chat_history[-4:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        history_str += f"{role}: {msg.get('content')}\n"
        
    prompt = f"""Given the following conversation history and a follow-up question, rewrite the follow-up question to be a standalone, self-contained search query. Do NOT answer the question. Just output the rewritten query.

Conversation History:
{history_str}

Follow-up Question: {question}

Standalone Rewritten Question:"""

    try:
        response = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=100,
            temperature=0.0
        )
        rewritten = response.choices[0].message.content.strip().strip('"').strip()
        print(f"[chat] Original: {question!r} -> Standalone Query: {rewritten!r}")
        return rewritten
    except Exception as e:
        print(f"[chat] Query rewriting failed: {e}")
        return question


def answer_question(bot_id, question, chat_history=None):
    """
    Main RAG function.
    Takes a bot_id, question, and optional chat history.
    Returns an answer from Groq based only on the website context.
    """
    if chat_history is None:
        chat_history = []

    # Step 1 — Rewrite query if history exists, then retrieve chunks
    search_query = rewrite_query(question, chat_history)
    print(f"\nSearching ChromaDB for: '{search_query}'")
    results = retrieve(bot_id, search_query, top_k=7)

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

    # Step 4 — Build system prompt instructions
    system_instruction = f"""You are a helpful AI assistant for a website. Follow these rules strictly:

1. **Answer ONLY from the context below.** Never use outside knowledge. Never make up information.
2. **Be specific** — include exact names, numbers, prices, dates if they appear in the context.
3. **Truncated text:** Website content may be truncated (e.g., titles ending in "..." or cut-off sentences). If the user asks for a specific item and you find a partial match that logically fits, assume it is the same item and answer based on what's available.
4. **Typo tolerance:** If the user's query has a minor typo or slightly different spelling (e.g., "reciepe" vs "recipe", "iPhone15" vs "iPhone 15"), still match it to relevant context.
5. **Synthesize multiple chunks:** If several context chunks mention the same topic, combine the information into one clear, coherent answer — do not repeat yourself.
6. **Preserve structure:** If the context contains tables, lists, or pricing tiers, format your answer in a structured way (use bullet points or numbered lists).
7. **If a specific product is not found**, do NOT suggest alternatives unless their names are nearly identical (e.g. same first word).
8. **If the answer is genuinely not in the context**, say exactly: "I don't have information about that on this website."

Context:
{context}"""

    # Step 5 — Construct message payload with history
    messages = [
        {"role": "system", "content": system_instruction}
    ]
    
    # Add conversation history
    for msg in chat_history:
        role = msg.get("role", "user")
        if role not in ["user", "assistant", "system"]:
            role = "user"
        messages.append({"role": role, "content": msg.get("content", "")})
        
    # Add current question
    messages.append({"role": "user", "content": question})

    # Step 6 — Call Groq API
    print("Calling Groq API...")
    response = groq_client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=messages,
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

    # Step 4 — Ask follow-up questions to test conversational memory
    print("\nStep 4: Testing conversational memory...\n")
    history = []
    
    q1 = "What is the price of Tipping the Velvet?"
    print(f"Q: {q1}")
    res1 = answer_question(bot_id, q1, history)
    print(f"A: {res1['answer']}")
    print(f"Sources: {res1['sources']}")
    print("-" * 50)
    
    # Add to history
    history.append({"role": "user", "content": q1})
    history.append({"role": "assistant", "content": res1["answer"]})

    # Q2 (Follow up using conversational memory)
    q2 = "Is it in stock?"
    print(f"Q: {q2}")
    res2 = answer_question(bot_id, q2, history)
    print(f"A: {res2['answer']}")
    print(f"Sources: {res2['sources']}")
    print("-" * 50)