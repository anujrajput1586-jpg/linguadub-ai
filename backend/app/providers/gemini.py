import time
import httpx
from app.core.config import settings
from app.providers.interfaces import TranslationProvider


class GeminiTranslationProvider(TranslationProvider):
    def translate(self, text: str, source: str, target: str, context: str = "") -> str:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for the Gemini translation provider.")
        prompt = f"Translate from {source} to {target}. Preserve technical terms and punctuation. Return only the translation.\n"
        if context:
            prompt += f"Nearby transcript context: {context}\n"
        prompt += f"Text: {text}"
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {"x-goog-api-key": settings.gemini_api_key}
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
        for attempt in range(3):
            try:
                response = httpx.post(url, headers=headers, json=payload, timeout=45)
                response.raise_for_status()
                return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError, KeyError, IndexError):
                if attempt == 2:
                    raise RuntimeError("Gemini translation request failed.") from None
                time.sleep(0.5 * (2 ** attempt))
        raise RuntimeError("Gemini translation request failed.")
