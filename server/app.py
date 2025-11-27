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
    raise ValueError("GEMINI_API_KEY missing!")

# BEST MODEL FOR INDIAN LANGUAGES (2025)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    'gemini-2.0-flash-exp',  # ← THIS IS THE KEY (experimental = better OCR)
    generation_config={
        "temperature": 0.1,
        "top_p": 1,
        "max_output_tokens": 2048
    }
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def extract_text(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))

    # INDIAN LANGUAGE SUPER PROMPT
    prompt = """
    You are the world's best OCR engine for Indian languages.
    Extract ALL text from this image EXACTLY as it appears.
    Support: Hindi (Devanagari), Tamil, Telugu, Kannada, Malayalam, Bengali, Gurmukhi (Punjabi), Gujarati, Odia, Arabic, English — even mixed.

    Rules:
    - Keep line breaks and spacing
    - Handle faded, tilted, artistic, or low-quality text
    - Do NOT translate — only extract raw text
    - If unsure, guess intelligently but don't hallucinate
    - Return ONLY the extracted text

    Image contains Indian signboard/text.
    """

    try:
        response = model.generate_content([prompt, img])
        return response.text.strip()
    except Exception as e:
        return "OCR failed"

def detect_language(text: str) -> str:
    if not text.strip():
        return "unknown"

    prompt = f"""
    Detect the main language of this text. Return ONLY the ISO code (2 letters).
    Prioritize Indian languages.

    Text: {text[:1000]}

    Examples:
    - "नमस्ते" → hi
    - "வணக்கம்" → ta
    - "నమస్కారం" → te
    - "नमस्ते" → hi
    - "হ্যালো" → bn
    - "hello" → en

    Answer ONLY the code:
    """

    try:
        response = model.generate_content(prompt)
        code = response.text.strip().lower()[:2]
        if code in ['hi','ta','te','kn','ml','bn','gu','pa','or','en','es','fr','de','ar','zh','ja','ko','ru','pt']:
            return code
    except:
        pass
    return "hi"  # fallback to Hindi (most common)

def translate_text(text: str, target_lang: str) -> str:
    if not text.strip():
        return "No text found"

    lang_names = {
        'hi': 'Hindi', 'ta': 'Tamil', 'te': 'Telugu', 'kn': 'Kannada', 'ml': 'Malayalam',
        'bn': 'Bengali', 'gu': 'Gujarati', 'pa': 'Punjabi', 'or': 'Odia',
        'en': 'English', 'es': 'Spanish', 'fr': 'French', 'ar': 'Arabic', 'zh': 'Chinese'
    }

    prompt = f"""
    Translate this Indian language text to {lang_names.get(target_lang, 'English')} naturally.
    Keep names, places, and numbers unchanged.
    Preserve tone and meaning perfectly.

    Text:
    {text}
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Translation failed"

@app.post("/translate-image")
async def translate_image(
    file: UploadFile = File(...),
    target_lang: str = Form("en")
):
    try:
        contents = await file.read()
        if len(contents) > 10_000_000:
            raise HTTPException(400, "Image too large")

        # Extract
        raw_text = extract_text(contents)
        if not raw_text or raw_text == "OCR failed":
            return {"error": "No text detected in image"}

        # Detect
        detected = detect_language(raw_text)

        # Translate
        translated = raw_text if detected == target_lang else translate_text(raw_text, target_lang)

        # Clean output
        original_clean = " ".join(line.strip() for line in raw_text.splitlines() if line.strip())
        translated_clean = " ".join(line.strip() for line in translated.splitlines() if line.strip())

        return {
            "detected_language": detected,
            "language_name": {
                'hi':'Hindi','ta':'Tamil','te':'Telugu','kn':'Kannada','ml':'Malayalam',
                'bn':'Bengali','gu':'Gujarati','pa':'Punjabi','en':'English'
            }.get(detected, detected.upper()),
            "original_text": original_clean or "No text",
            "translated_text": translated_clean or "Translation failed",
            "target_language": target_lang
        }

    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")