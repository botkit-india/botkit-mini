"""
chat.py — RAG Chat Engine for BotKit India
Takes a user question, retrieves relevant context from ChromaDB,
and generates a response using Groq API (llama-3.1-8b-instant).
"""

import os
import logging
from groq import Groq
from dotenv import load_dotenv
from embedder import search

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "llama-3.1-8b-instant")

# System prompt for the RAG bot
SYSTEM_PROMPT = """You are BotKit — a helpful AI assistant that answers questions based on the provided context from crawled web pages.

RULES:
1. Answer ONLY based on the provided context. Do not make up information.
2. If the context doesn't contain enough information to answer, say: "I don't have enough information from the crawled pages to answer that question. Try crawling more relevant URLs."
3. Be concise but thorough. Use bullet points for clarity when appropriate.
4. Always mention which source(s) your answer is based on when possible.
5. If the user asks something completely unrelated to the context, politely redirect them.

CONTEXT FORMAT:
You'll receive relevant text chunks from crawled web pages along with their source URLs. Use this information to formulate your answer."""


def build_context(query: str, n_results: int = 5) -> tuple[str, list[dict]]:
    """
    Retrieve relevant chunks from ChromaDB and format them as context.
    
    Args:
        query: The user's question
        n_results: Number of chunks to retrieve
        
    Returns:
        Tuple of (formatted_context_string, list_of_source_metadata)
    """
    results = search(query, n_results=n_results)

    if not results:
        return "", []

    context_parts = []
    sources = []

    for i, result in enumerate(results):
        source_url = result["metadata"].get("source_url", "Unknown")
        title = result["metadata"].get("title", "Unknown")
        relevance = result.get("relevance", 0)

        context_parts.append(
            f"[Source {i+1}: {title} ({source_url}) — Relevance: {relevance}]\n"
            f"{result['text']}\n"
        )

        sources.append({
            "url": source_url,
            "title": title,
            "relevance": relevance,
        })

    context = "\n---\n".join(context_parts)
    return context, sources


def chat(query: str, conversation_history: list[dict] | None = None) -> dict:
    """
    Main chat function — performs RAG query and returns LLM response.
    
    Args:
        query: The user's question
        conversation_history: Optional list of previous messages for multi-turn chat
        
    Returns:
        Dictionary with answer, sources, and metadata
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_key_here":
        return {
            "answer": "⚠️ Groq API key not configured. Please set GROQ_API_KEY in your .env file.",
            "sources": [],
            "error": "missing_api_key"
        }

    # Step 1: Retrieve relevant context
    logger.info(f"💬 Query: {query}")
    context, sources = build_context(query)

    if not context:
        return {
            "answer": "I don't have any information yet. Please crawl some URLs first using the /crawl endpoint or the web interface.",
            "sources": [],
            "error": "no_context"
        }

    # Step 2: Build messages for the LLM
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history if provided (for multi-turn)
    if conversation_history:
        messages.extend(conversation_history[-6:])  # Keep last 6 messages for context

    # Add the current query with context
    user_message = (
        f"CONTEXT FROM CRAWLED PAGES:\n\n{context}\n\n"
        f"---\n\n"
        f"USER QUESTION: {query}"
    )
    messages.append({"role": "user", "content": user_message})

    # Step 3: Call Groq API
    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.3,  # Lower temperature for more factual responses
            top_p=0.9,
        )

        answer = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        logger.info(f"✅ Response generated ({usage['total_tokens']} tokens)")

        return {
            "answer": answer,
            "sources": sources,
            "usage": usage,
            "model": LLM_MODEL,
        }

    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return {
            "answer": f"Error generating response: {str(e)}",
            "sources": sources,
            "error": str(e)
        }


if __name__ == "__main__":
    # Interactive chat test
    print("🤖 BotKit Chat (type 'quit' to exit)")
    print("-" * 40)

    history = []
    while True:
        query = input("\nYou: ").strip()
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue

        result = chat(query, history)
        print(f"\nBot: {result['answer']}")

        if result.get("sources"):
            print(f"\n📚 Sources:")
            for s in result["sources"]:
                print(f"   • {s['title']} ({s['url']})")

        # Track history for multi-turn
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": result["answer"]})
