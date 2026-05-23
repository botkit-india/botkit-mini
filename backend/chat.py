"""
chat.py -- Multi-Language + Conversational Memory RAG
-----------------------------------------------------
Author  : Manav
Branch  : manav/dev

Features:
- Conversational Memory (history support)
- Query Rewriting (uses history to create a self-contained search query)
- Multi-Language Support (auto-detect + translate via Groq LLM)
"""

import os
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path
from embedder import retrieve

# Load .env file to get GROQ_API_KEY
load_dotenv(Path(__file__).parent / '.env')

# Initialize Groq client
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# Supported language names for prompt generation
LANG_NAMES = {
    'en': 'English', 'hi': 'Hindi', 'es': 'Spanish', 'fr': 'French',
    'de': 'German', 'ja': 'Japanese', 'zh': 'Chinese', 'ar': 'Arabic',
    'pt': 'Portuguese', 'ko': 'Korean', 'ru': 'Russian', 'bn': 'Bengali',
    'ta': 'Tamil', 'te': 'Telugu', 'mr': 'Marathi', 'gu': 'Gujarati',
    'kn': 'Kannada', 'ml': 'Malayalam', 'pa': 'Punjabi', 'ur': 'Urdu',
    'it': 'Italian', 'nl': 'Dutch', 'tr': 'Turkish', 'th': 'Thai',
    'vi': 'Vietnamese', 'id': 'Indonesian', 'ms': 'Malay', 'sw': 'Swahili'
}


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


def detect_language(text):
    """
    Use LLM to detect the language of the user's input.
    Returns a language code like 'en', 'hi', 'es', 'fr', etc.
    """
    prompt = f"""Detect the language of the following text. 
Reply with ONLY the ISO 639-1 language code (e.g., en, hi, es, fr, de, ja, zh, ar, pt, ko, ru, bn, ta, te, mr, gu, kn, ml, pa, ur).
If you're unsure, reply with 'en'.

Text: {text}

Language code:"""

    try:
        response = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=5,
            temperature=0.0
        )
        lang = response.choices[0].message.content.strip().lower()[:2]
        print(f"[chat] Detected language: {lang}")
        return lang
    except Exception as e:
        print(f"[chat] Language detection failed: {e}")
        return "en"


def translate_text(text, source_lang, target_lang):
    """
    Translate text from source_lang to target_lang using LLM.
    If source and target are the same, return text as-is.
    """
    if source_lang == target_lang:
        return text

    src_name = LANG_NAMES.get(source_lang, source_lang)
    tgt_name = LANG_NAMES.get(target_lang, target_lang)

    prompt = f"""Translate the following text from {src_name} to {tgt_name}.
Output ONLY the translated text. Do not add any explanation.

Text: {text}

Translation:"""

    try:
        response = groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=600,
            temperature=0.1
        )
        translated = response.choices[0].message.content.strip()
        print(f"[chat] Translated ({src_name} -> {tgt_name}): {translated[:80]}...")
        return translated
    except Exception as e:
        print(f"[chat] Translation failed: {e}")
        return text  # Fallback: return original text


def answer_question(bot_id, question, chat_history=None, language=None):
    """
    Main RAG function.
    Takes a bot_id, question, and optional chat history.
    Returns an answer from Groq based only on the website context.
    Now supports multi-language: detects user language, searches in English, responds in user's language.
    """
    if chat_history is None:
        chat_history = []

    # Step 0 — Detect user's language (or use the one passed in)
    user_lang = language or detect_language(question)

    # Step 0.5 — Translate question to English for RAG search (if not already English)
    english_question = translate_text(question, user_lang, "en") if user_lang != "en" else question

    # Step 1 — Rewrite query if history exists, then retrieve chunks (always in English)
    search_query = rewrite_query(english_question, chat_history)
    print(f"\nSearching ChromaDB for: '{search_query}'")
    results = retrieve(bot_id, search_query, top_k=7)

    if not results:
        no_info_msg = (
            "I'm sorry, but I don't have any information from this website yet. "
            "Please crawl the website first, and then I'll be happy to help."
        )
        if user_lang != "en":
            no_info_msg = translate_text(no_info_msg, "en", user_lang)
        return {
            'answer': no_info_msg,
            'sources': [],
            'language': user_lang
        }

    # Step 2 — Build context from retrieved chunks
    context = '\n---\n'.join([r['text'] for r in results])

    # Step 3 — Get unique source URLs
    sources = list(set(r['source_url'] for r in results))
    print(f"Found {len(results)} relevant chunks from {len(sources)} pages")

    # Step 4 — Build system prompt instructions (with language instruction)
    response_lang = LANG_NAMES.get(user_lang, 'English')

    system_instruction = f"""You are a helpful AI assistant for a website. Follow these rules strictly:

1. **Answer ONLY from the context below.** Never use outside knowledge. Never make up information.
2. **Be specific** — include exact names, numbers, prices, dates if they appear in the context.
3. **Truncated text:** Website content may be truncated (e.g., titles ending in "..." or cut-off sentences). If the user asks for a specific item and you find a partial match that logically fits, assume it is the same item and answer based on what's available.
4. **Typo tolerance:** If the user's query has a minor typo or slightly different spelling (e.g., "reciepe" vs "recipe", "iPhone15" vs "iPhone 15"), still match it to relevant context.
5. **Synthesize multiple chunks:** If several context chunks mention the same topic, combine the information into one clear, coherent answer — do not repeat yourself.
6. **Preserve structure:** If the context contains tables, lists, or pricing tiers, format your answer in a structured way (use bullet points or numbered lists).
7. **If a specific product is not found**, do NOT suggest alternatives unless their names are nearly identical (e.g. same first word).
8. **If the answer is genuinely not in the context**, reply gently and briefly. Use wording like: "I'm sorry, but I couldn't find that information on this website. If you'd like, I can still help with questions about the content available here."
9. **For out-of-scope questions**, be polite and never sound abrupt, dismissive, or robotic.

IMPORTANT: You MUST respond in {response_lang} language.

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
        'sources': sources,
        'language': user_lang
    }


# ---- TEST BLOCK ----
if __name__ == "__main__":
    from crawler import crawl_website
    from embedder import embed_and_store

    print("=== FULL RAG PIPELINE TEST (with Multi-Language) ===\n")

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

    # Step 3 — Ask questions in multiple languages
    print("Step 3: Multi-language questions...\n")

    history = []
    
    # Q1 — English
    q1 = "What is the price of Tipping the Velvet?"
    print(f"Q (English): {q1}")
    res1 = answer_question(bot_id, q1, history)
    print(f"A: {res1['answer']}")
    print(f"Detected Language: {res1['language']}")
    print("-" * 50)
