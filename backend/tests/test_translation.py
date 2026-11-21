from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.database import Base
from app.models.entities import GlossaryTerm, Project, Segment
from app.services.translation import translate_project


def test_glossary_terms_are_enforced_and_segments_receive_context(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    observed = []

    def fake_translate(self, text, source, target, context=""):
        observed.append((text, context))
        return f"Translated {text}"

    monkeypatch.setattr("app.providers.translation.GoogleTranslationProvider.translate", fake_translate)
    with Session(engine) as db:
        project = Project(title="Repair", source_path="video.mp4", source_language="zh", target_language="hi")
        project.segments.extend([
            Segment(start=0, end=2, original_text="主轴 alignment"),
            Segment(start=2, end=4, original_text="Check bearing temperature"),
        ])
        db.add(project)
        db.add(GlossaryTerm(source_term="主轴", target_term="स्पिंडल", source_language="zh", target_language="hi"))
        db.commit()
        translate_project(db, project)
        assert "स्पिंडल" in project.segments[0].translated_text
        assert "主轴" not in project.segments[0].translated_text
        assert observed[0][1] == "Previous/next segment context: Check bearing temperature"
        assert "LINGUADUBTERM" in observed[0][0]
