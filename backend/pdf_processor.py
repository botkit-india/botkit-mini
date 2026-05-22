import PyPDF2
import io
from embedder import append_and_store

def extract_text_from_pdf(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Extract text from PDF file bytes.
    Returns list of pages in same format as crawler:
    [{url, text}, {url, text}, ...]
    """
    pages = []
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        print(f"[pdf] Processing {filename} — {len(pdf_reader.pages)} pages")

        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text and len(text.strip()) > 50:
                # Clean up text
                text = ' '.join(text.split())
                pages.append({
                    'url': f"pdf://{filename}#page{i+1}",
                    'text': text
                })
                print(f"[pdf] Page {i+1}: {len(text)} chars extracted")

        print(f"[pdf] Total pages extracted: {len(pages)}")
        return pages

    except Exception as e:
        print(f"[pdf] Error processing {filename}: {e}")
        raise


def process_and_embed_pdf(bot_id: str, file_bytes: bytes, filename: str) -> int:
    """
    Extract text from PDF and embed into existing bot's ChromaDB collection.
    Returns number of chunks added.
    """
    pages = extract_text_from_pdf(file_bytes, filename)

    if not pages:
        raise ValueError("No text could be extracted from this PDF.")

    append_and_store(bot_id, pages)
    return len(pages)