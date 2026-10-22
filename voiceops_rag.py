# -*- coding: utf-8 -*-
"""
VoiceOps Capstone - ZentroMart RAG Chatbot
"""

from pathlib import Path
import os
import re
import time
from google import genai

# --------------------------------------------------
# 1. DATASET PATH
# --------------------------------------------------

BASE_DIR = Path(
    r"C:\Users\HP\Downloads\Capstone_Project_Dataset_FTTT_2026"
    r"\Capstone_Project_Dataset_FTTT_2026"
)

KB_DIR = BASE_DIR / "kb"

if not KB_DIR.exists():
    raise FileNotFoundError(
        f"Knowledge base folder not found: {KB_DIR}\n"
        "Please check the dataset folder path."
    )

# --------------------------------------------------
# 2. GEMINI API SETUP
# --------------------------------------------------

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. Check your Windows "
        "environment variable and restart Spyder."
    )

client = genai.Client(api_key=api_key)

MODEL = "gemini-3.8-flash"



# --------------------------------------------------
# 3. LOAD MARKDOWN DOCUMENTS
# --------------------------------------------------

sections = []

for path in sorted(KB_DIR.glob("*.md")):
    file_text = path.read_text(encoding="utf-8")
    current_heading = path.name
    buffer = []

    for line in file_text.splitlines():
        if line.startswith("#"):
            if buffer:
                body = "\n".join(buffer).strip()

                if body:
                    sections.append({
                        "source": path.name,
                        "heading": current_heading,
                        "text": body
                    })

            buffer = []
            current_heading = line.lstrip("#").strip()

        else:
            buffer.append(line)

    if buffer:
        body = "\n".join(buffer).strip()

        if body:
            sections.append({
                "source": path.name,
                "heading": current_heading,
                "text": body
            })

if not sections:
    raise ValueError("No document sections found in kb folder.")

print(f"Loaded {len(sections)} document sections.")

# --------------------------------------------------
# 4. TOKENIZATION
# --------------------------------------------------

def tokenize(text):
    words = set(re.findall(r"[a-z0-9]+", text.lower()))

    if "return" in words:
        words.add("returns")

    if "refund" in words:
        words.add("refunds")

    return words


documents = [
    item["heading"] + "\n" + item["text"]
    for item in sections
]

# --------------------------------------------------
# 5. RETRIEVAL
# --------------------------------------------------

def retrieve(question, top_k=4):
    query_words = tokenize(question)
    # Expand common customer wording
    q = question.lower()

    if any(word in q for word in [
        "damaged", "damage", "broken",
        "defective", "wrong item"
    ]):
        query_words.update(tokenize(
            "damaged wrong missing item return "
            "replacement report 48 hours"
        ))

    if not query_words:
        return []

    scored_sections = []

    for item, document in zip(sections, documents):
        document_words = tokenize(document)
        overlap = query_words & document_words

        if overlap:
            result = item.copy()
            result["score"] = (
                len(overlap) / len(query_words)
            )
            scored_sections.append(result)

    scored_sections.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return scored_sections[:top_k]


# --------------------------------------------------
# 6. GEMINI RESPONSE WITH RETRIES
# --------------------------------------------------

def respond(question):
    matches = retrieve(question)

    if not matches:
        return (
            "I could not find relevant information in "
            "the company documents. I cannot confirm "
            "the answer.",
            []
        )

    context = "\n\n".join(
        f"Source: {item['source']}\n"
        f"Section: {item['heading']}\n"
        f"{item['text']}"
        for item in matches
    )

    prompt = f"""
You are the AI customer support assistant for ZentroMart.

Instructions:
- Answer using only the document excerpts provided.
- Use simple, polite language.
- Do not invent policies, dates, fees, or promises.
- If the excerpts do not fully answer the question,
  clearly state that you cannot confirm the missing details.
- Do not claim that an order was checked or a ticket created.
- Mention relevant policy conditions when available.

DOCUMENT EXCERPTS:
{context}

CUSTOMER QUESTION:
{question}

Write a concise answer for the customer.
"""

    response = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )
            break

        except Exception as error:
            error_text = str(error)

            is_temporary = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
            )

            if is_temporary and attempt < 2:
                wait_seconds = 5 * (attempt + 1)

                print(
                    f"Gemini temporarily unavailable. "
                    f"Retrying in {wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)

            else:
                print("Gemini API request failed:")
                print(error_text)

                return (
                    "Sorry, I could not generate an answer "
                    "right now. Please try again later.",
                    [
                        f"{item['source']} — {item['heading']}"
                        for item in matches
                    ]
                )

    if response is None or not response.text:
        return (
            "Sorry, Gemini did not return a text answer.",
            [
                f"{item['source']} — {item['heading']}"
                for item in matches
            ]
        )

    sources = [
        f"{item['source']} — {item['heading']}"
        for item in matches
    ]

    return response.text, sources


# --------------------------------------------------
# 7. RUN CHATBOT
# --------------------------------------------------

if __name__ == "__main__":

    print("\nZentroMart RAG Chatbot")
    print("-" * 40)

    question = "I received a damage item.what should I do?"

    print("Customer:", question)
    print("\nGenerating answer using Gemini...")

    answer, sources = respond(question)

    print("\nGemini's Answer:")
    print(answer)

    print("\nRetrieved Sources:")

    for source in sources:
        print("-", source)

    print("\nTest completed.")