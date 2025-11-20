# server/global_translator.py
import google.generativeai as genai

# Global languages map (examples; expand as needed)
GLOBAL_LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "zh": "Chinese",
    "ar": "Arabic", "ru": "Russian", "ja": "Japanese", "de": "German",
    "ko": "Korean", "it": "Italian", "pt": "Portuguese"
}

def detect_global_language(model, text: str) -> dict:
    if not text.strip():
        return {"code": "unknown", "name": "Unknown", "region": "global"}

    prompt = f"""
    Detect global language (e.g., Latin, Cyrillic, Arabic).
    Return JSON: {{"code": "en", "name": "English"}}
    Text: {text[:1500]}
    """
    response = model.generate_content(prompt)
    import json
    try:
        result = json.loads(response.text.strip("```json").strip("```"))
        code = result.get("code", "unknown").lower()
        if code in GLOBAL_LANGUAGES:
            return {"code": code, "name": GLOBAL_LANGUAGES[code], "region": "global"}
    except:
        pass
    return {"code": "unknown", "name": "Unknown", "region": "global"}

def translate_global_text(model, text: str, target_lang: str, lang_info: dict) -> str:
    if not text.strip():
        return ""

    source_name = lang_info["name"]
    target_name = GLOBAL_LANGUAGES.get(target_lang.lower(), target_lang)

    prompt = f"""
    Translate global text from {source_name} to {target_name}.
    Preserve tone, formatting; handle RTL for Arabic.
    Return ONLY translated text.
    Text: {text}
    """
    response = model.generate_content(prompt)
    return response.text.strip()