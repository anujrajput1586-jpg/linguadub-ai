import re
from deep_translator import GoogleTranslator
from app.providers.interfaces import TranslationProvider


class GoogleTranslationProvider(TranslationProvider):
    def translate(self, text: str, source: str, target: str, context: str = "") -> str:
        source_code = "auto" if source == "auto" else source
        if context:
            marker = "LINGUADUB_CURRENT_SEGMENT"
            contextual_text = f"{context}\n{marker}\n{text}\n{marker}"
            translated = GoogleTranslator(source=source_code, target=target).translate(contextual_text)
            pieces = translated.split(marker)
            if len(pieces) >= 3:
                return pieces[1].strip()
        return GoogleTranslator(source=source_code, target=target).translate(text)


def protect_glossary(text: str, terms: list[tuple[str, str]]) -> tuple[str, dict[str, str]]:
    protected = text
    tokens: dict[str, str] = {}
    for index, (source_term, target_term) in enumerate(sorted(terms, key=lambda item: len(item[0]), reverse=True)):
        if not source_term:
            continue
        token = f"LINGUADUBTERM{index:04d}TOKEN"
        protected, count = re.subn(re.escape(source_term), token, protected, flags=re.IGNORECASE)
        if count:
            tokens[token] = target_term
    return protected, tokens


def restore_glossary(text: str, tokens: dict[str, str]) -> str:
    for token, target_term in tokens.items():
        text = re.sub(re.escape(token), lambda _: target_term, text, flags=re.IGNORECASE)
    return text
