# server/app.py
import os
import io
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY missing in .env")

genai.configure(api_key=GEMINI_API_KEY)

# SWITCH TO BETTER MODEL FOR OCR (2.0 Flash excels in multilingual OCR per 2025 benchmarks)
model = genai.GenerativeModel('gemini-2.0-flash')

app = FastAPI(title="Lens Translator – Fixed OCR & Translation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

def validate_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image")
    image_bytes = file.file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image >10MB")
    try:
        Image.open(io.BytesIO(image_bytes)).verify()
    except:
        raise HTTPException(status_code=400, detail="Invalid image file")
    return image_bytes

def extract_text(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    # IMPROVED PROMPT: Explicit for multilingual OCR, preserves formatting, focuses on accuracy
    prompt = """
    Extract ALL visible text from this image EXACTLY as it appears.
    Preserve:
    - Line breaks, spacing, tables, lists
    - All scripts: Devanagari (Hindi/Marathi), Tamil, Telugu, Kannada, Malayalam, Bengali, Gurmukhi (Punjabi), Arabic (RTL), Latin, Cyrillic, Chinese, etc.
    - Numbers, symbols, punctuation

    For low-quality text, use best guess but mark uncertain with [?].
    Return ONLY the extracted text. No explanations or extra words.
    """
    response = model.generate_content([prompt, img], generation_config={"temperature": 0.1, "max_output_tokens": 2000})
    return response.text.strip()

def detect_language(text: str) -> str:
    if not text.strip():
        return "unknown"
    # IMPROVED PROMPT: Structured JSON for reliability; focuses on ISO codes with Indian/global bias
    prompt = f"""
    Detect the primary language/script in this text.
    Return ONLY JSON: {{"code": "ISO-639-1 code (e.g. 'hi', 'ta', 'en')", "confidence": 0-1}}

    Prioritize Indian languages: Hindi (hi/Devanagari), Tamil (ta), Telugu (te), Kannada (kn), Malayalam (ml), Bengali (bn), etc.
    Global: English (en), Spanish (es), Arabic (ar), Chinese (zh), etc.
    If mixed, choose dominant. Low confidence if unclear.

    Text: {text[:1500]}
    """
    response = model.generate_content(prompt, generation_config={"temperature": 0, "max_output_tokens": 50})
    try:
        result = json.loads(response.text.strip("```json").strip("```"))
        code = result.get("code", "unknown").lower()
        if len(code) == 2 and code.isalpha():
            return code
    except:
        pass
    return "unknown"

def translate_text(text: str, target_lang: str, detected_lang: str) -> str:
    if not text.strip():
        return ""
    # IMPROVED PROMPT: Cultural nuance, formatting preservation, examples for accuracy
    lang_map = {
        "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam", "bn": "Bengali",
        "en": "English", "es": "Spanish", "fr": "French", "ar": "Arabic", "zh": "Chinese"
    }
    source_name = lang_map.get(detected_lang, detected_lang)
    target_name = lang_map.get(target_lang.lower(), target_lang)

    prompt = f"""
    Translate this {source_name} text to {target_name}.
    Rules:
    - Preserve exact meaning, tone, cultural references, proper nouns (e.g., names/places unchanged)
    - Keep line breaks, spacing, tables/lists, punctuation, numbers
    - For Indian languages: Handle scripts accurately (Devanagari/Tamil); don't anglicize words
    - Example: "श्री गणेश मंदिर" → "Shri Ganesh Temple" (not "Mr. Ganesh Temple")

    Return ONLY the translated text. No explanations.

    Text:
    {text}
    """
    response = model.generate_content(prompt, generation_config={"temperature": 0.2, "max_output_tokens": 1500})
    return response.text.strip()

@app.post("/translate-image")
async def translate_image(file: UploadFile = File(...), target_lang: str = Form("en")):
    try:
        image_bytes = validate_image(file)
        raw_text = extract_text(image_bytes)
        cleaned_text = " ".join(line.strip() for line in raw_text.splitlines() if line.strip()) if raw_text else ""

        if not cleaned_text:
            return {"error": "No text detected"}

        detected_lang = detect_language(raw_text)  # Use raw for better detection

        if detected_lang == target_lang.lower():
            translated_text = raw_text
        else:
            translated_text = translate_text(raw_text, target_lang, detected_lang)

        return {
            "detected_language": detected_lang,
            "language_name": {  # Add names for frontend
                "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam", "bn": "Bengali",
                "es": "Spanish", "fr": "French", "ar": "Arabic", "zh": "Chinese", "en": "English"
            }.get(detected_lang, detected_lang.upper()),
            "original_text": cleaned_text,
            "translated_text": " ".join(line.strip() for line in translated_text.splitlines() if line.strip()),
            "target_language": target_lang
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")