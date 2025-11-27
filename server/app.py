# server/app.py
import io
import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import google.generativeai as genai

# === CONFIG ===
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# This model is currently the absolute best for Indian languages + real-world signs (Aug–Nov 2025)
model = genai.GenerativeModel(
    "gemini-1.5-flash-002",
    generation_config={"temperature": 0.0, "top_p": 0.95, "max_output_tokens": 8192},
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/translate-image")
async def translate_image(file: UploadFile = File(...), target_lang: str = Form("en")):
    # Read image
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes))

    # SUPER PROMPT — THIS IS WHAT MAKES IT WORK ON EVERY INDIAN SIGNBOARD
    prompt = """
You are the most accurate OCR + robust OCR + translator for Indian street signs, shop boards, menus, banners, and posters.

Step 1 → Extract ALL text from the image EXACTLY as shown (preserve line breaks, spacing, and order).
Step 2 → Detect the main language (return only the 2-letter code).
Step 3 → If the detected language is NOT the target language, translate the extracted text naturally and accurately to the target language.
Step 4 → Return JSON in this exact format (no extra text):

{
  "original_text": "extracted text here",
  "detected_language": "hi",
  "translated_text": "translated text here (or same as original if already in target language)"
}

Supported languages and codes:
hi=Hindi, ta=Tamil, te=Telugu, kn=Kannada, ml=Malayalam, bn=Bengali, pa=Punjabi, gu=Gujarati, or=Odia,
en=English, es=Spanish, fr=French, de=German, ar=Arabic, zh=Chinese, ja=Japanese, ko=Korean, ru=Russian, pt=Portuguese

Target language code received: """ + target_lang + """

Extract and translate now.
"""

    try:
        response = model.generate_content([prompt, image])
        result = response.text.strip()

        # Clean ```json blocks if present
        if result.startswith("```json"):
            result = result[7:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()

        import json
        data = json.loads(result)

        # Final clean output for frontend
        return {
            "detected_language": data.get("detected_language", "unknown"),
            "language_name": {
                "hi":"Hindi","ta":"Tamil","te":"Telugu","kn":"Kannada","ml":"Malayalam",
                "bn":"Bengali","pa":"Punjabi","gu":"Gujarati","or":"Odia","en":"English"
            }.get(data.get("detected_language", ""), data.get("detected_language", "").upper()),
            "original_text": data.get("original_text", "").strip() or "No text found",
            "translated_text": data.get("translated_text", "").strip() or "Translation failed",
            "target_language": target_lang
        }

    except Exception as e:
        return {"error": f"Processing failed: {str(e)}"}