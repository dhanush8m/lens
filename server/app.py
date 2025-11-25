# server/app.py
import os
import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY missing in .env")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

app = FastAPI(title="Lens Translator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allows your frontend (any URL)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

def validate_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="Unsupported image")
    data = file.file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image >10MB")
    Image.open(io.BytesIO(data)).verify()
    return data

def ocr(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    resp = model.generate_content(["Extract ALL text. Return ONLY the text.", img])
    return resp.text.strip()

def detect_lang(text: str) -> str:
    if not text.strip():
        return "unknown"
    resp = model.generate_content(
        f"Return ONLY the ISO‑639‑1 code (e.g. hi, en) of this text:\n{text[:1000]}"
    )
    code = resp.text.strip().lower()
    return code if len(code) == 2 and code.isalpha() else "unknown"

def translate(text: str, target: str) -> str:
    if not text.strip():
        return ""
    resp = model.generate_content(
        f"Translate to {target}. Preserve formatting. Return ONLY translation.\n\n{text}"
    )
    # Remove all line-breaks and join with a single space
    return " ".join(line.strip() for line in resp.text.splitlines() if line.strip())
def clean_text(text: str) -> str:
    """
    Remove newlines and extra spaces. Convert multi-line text to single line.
    """
    if not text:
        return ""
    return " ".join(line.strip() for line in text.splitlines() if line.strip())

@app.post("/translate-image")
async def translate_image(file: UploadFile = File(...), target_lang: str = Form("en")):
    try:
        img_bytes = validate_image(file)
        raw_text = ocr(img_bytes)
        cleaned_text = clean_text(raw_text)

        if not cleaned_text:
            return {"error": "No text found"}

        src = detect_lang(cleaned_text)

        if src == target_lang.lower():
            cleaned_translated = cleaned_text
        else:
            raw_translated = translate(raw_text, target_lang)
            cleaned_translated = clean_text(raw_translated)

        return {
            "detected_language": src,
            "original_text": cleaned_text,
            "translated_text": cleaned_translated,
            "target_language": target_lang
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))