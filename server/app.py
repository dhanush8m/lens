# server/app.py — ONLY CHANGE: clean line-by-line output (no \n)
import os
import io
import json
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Add GEMINI_API_KEY in .env file!")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/translate-image")
async def translate_image(file: UploadFile = File(...), target_lang: str = Form("en")):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))

        prompt = f"""
Extract ALL text from this image exactly as shown.
Detect the main language (return only 2-letter code like hi, ta, te, en).
If not already in {target_lang}, translate naturally.

Return ONLY this JSON:
{{
  "original_text": "extracted text",
  "detected_language": "hi",
  "translated_text": "translated text"
}}

Target language: {target_lang}
"""

        response = model.generate_content([prompt, image])
        raw = response.text.strip()

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1]

        data = json.loads(raw)

        lang_names = {
            "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam",
            "bn": "Bengali", "gu": "Gujarati", "pa": "Punjabi", "or": "Odia", "en": "English"
        }

        # ONLY CHANGE STARTS HERE — clean line-by-line lists
        def clean_lines(text):
            if not text:
                return []
            return [line.strip() for line in text.split("\n") if line.strip()]

        original_lines = clean_lines(data.get("original_text"))
        translated_lines = clean_lines(data.get("translated_text"))

        return {
            "detected_language": data.get("detected_language", "unknown"),
            "language_name": lang_names.get(data.get("detected_language", ""), "Unknown"),
            "original_text": original_lines,       # ← now a list
            "translated_text": translated_lines,   # ← now a list
            "target_language": target_lang
        }
        # ONLY CHANGE ENDS HERE

    except Exception as e:
        return {"error": f"Failed: {str(e)}"}