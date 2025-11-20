# server/indian_translator.py
import google.generativeai as genai

# Indian languages map
INDIAN_LANGUAGES = {
    "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada",
    "ml": "Malayalam", "bn": "Bengali", "gu": "Gujarati", "pa": "Punjabi",
    "mr": "Marathi", "ur": "Urdu", "or": "Odia", "as": "Assamese",
    "ks": "Kashmiri", "ne": "Nepali", "sd": "Sindhi", "si": "Sinhala"
}

def detect_indian_language(model, text: str) -> dict:
    if not text.strip():
        return {"code": "unknown", "name": "Unknown", "region": "india"}

    prompt = f"""
    Detect language from Indian scripts only (e.g., Devanagari, Tamil).
    Return JSON: {{"code": "hi", "name": "Hindi"}}
    Text: {text[:1500]}
    """
    response = model.generate_content(prompt)
    import json
    try:
        result = json.loads(response.text.strip("```json").strip("```"))
        code = result.get("code", "unknown").lower()
        if code in INDIAN_LANGUAGES:
            return {"code": code, "name": INDIAN_LANGUAGES[code], "region": "india"}
    except:
        pass
    return {"code": "unknown", "name": "Unknown", "region": "india"}

def translate_indian_text(model, text: str, target_lang: str, lang_info: dict) -> str:
    if not text.strip():
        return ""

    source_name = lang_info["name"]
    target_name = INDIAN_LANGUAGES.get(target_lang.lower(), target_lang)

    prompt = f"""
    Translate Indian text from {source_name} to {target_name}.
    Preserve cultural terms, Devanagari/Tamil scripts if needed.
    Return ONLY translated text.
    Text: {text}
    """
    response = model.generate_content(prompt)
    return response.text.strip()