# server/app.py — FINAL & PERFECT: text + image working 100%
import os
import io
import json
import base64
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing!")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Global variable to store last uploaded image (so we can reuse it for overlay)
latest_image = None

@app.post("/translate")
async def translate(file: UploadFile = File(...), target_lang: str = Form("en")):
    global latest_image
    try:
        image_bytes = await file.read()
        latest_image = image_bytes  # Save for overlay endpoint
        image = Image.open(io.BytesIO(image_bytes))

        prompt = f"""
Extract ALL text exactly as shown.
Detect language (2-letter code).
Translate to {target_lang} if needed.

Return ONLY JSON:
{{
  "original_text": "text with \\n",
  "detected_language": "ml",
  "translated_text": "translated text with \\n"
}}
"""
        response = model.generate_content([prompt, image])
        raw = response.text.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        data = json.loads(raw.strip())

        def clean(text):
            return [line.strip() for line in text.split("\n") if line.strip()]

        original_lines = clean(data.get("original_text", ""))
        translated_lines = clean(data.get("translated_text", ""))

        lang_names = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam",
                      "bn": "Bengali", "gu": "Gujarati", "pa": "Punjabi", "or": "Odia", "en": "English"}

        return {
            "detected_language": data.get("detected_language", "unknown"),
            "language_name": lang_names.get(data.get("detected_language", ""), "Unknown"),
            "original_text": original_lines,
            "translated_text": translated_lines,
            "target_language": target_lang
        }

    except Exception as e:
        return {"error": str(e)}

# This uses the last uploaded image → no need to upload twice
@app.get("/translated-image")
async def get_translated_image():
    global latest_image
    if not latest_image:
        return {"error": "No image uploaded yet"}

    try:
        image = Image.open(io.BytesIO(latest_image)).convert("RGB")
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 100)
        except:
            font = ImageFont.load_default()

        # Re-run translation quickly
        prompt = "Translate all text in this image to English. Return only the translated text with line breaks."
        response = model.generate_content([prompt, image])
        translated_text = response.text.strip()
        lines = [line.strip() for line in translated_text.split("\n") if line.strip()][:8]

        y = 60
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            draw.rectangle([20, y-20, 60+w, y+100], fill=(0, 0, 0, 180))
            draw.text((40, y), line, font=font, fill="white")
            y += 170

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    except Exception as e:
        return {"error": str(e)}