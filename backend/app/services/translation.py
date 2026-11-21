from sqlalchemy.orm import Session
from app.core.languages import LANGUAGES
from app.models.entities import GlossaryTerm, Project
from app.providers.factory import get_translation_provider
from app.providers.translation import protect_glossary, restore_glossary


def translate_project(db: Session, project: Project, segment_id: int | None = None) -> None:
    provider = get_translation_provider()
    segments = sorted(project.segments, key=lambda item: item.start)
    if not segments:
        raise ValueError("Transcribe this project before translating it.")
    selected = [item for item in segments if segment_id is None or item.id == segment_id]
    if segment_id is not None and not selected:
        raise LookupError("Segment not found.")
    source = project.detected_language or project.source_language
    target = project.target_language
    terms = db.query(GlossaryTerm).filter(GlossaryTerm.target_language == target).all()
    applicable_terms = [(term.source_term, term.target_term) for term in terms if term.source_language in {"auto", source}]
    if target not in LANGUAGES:
        raise ValueError("Unsupported target language.")
    for index, segment in enumerate(segments):
        if segment not in selected:
            continue
        context_parts = []
        if index:
            context_parts.append(segments[index - 1].original_text)
        if index + 1 < len(segments):
            context_parts.append(segments[index + 1].original_text)
        protected, tokens = protect_glossary(segment.original_text, applicable_terms)
        context = "Previous/next segment context: " + " | ".join(context_parts) if context_parts else ""
        translated = provider.translate(protected, source, target, context)
        segment.translated_text = restore_glossary(translated.strip(), tokens)
    project.target_language = target
    project.status = "awaiting_review"
    project.current_step = "Review translation"
    project.progress = max(project.progress, 65)
    project.error_message = None
    db.commit()
