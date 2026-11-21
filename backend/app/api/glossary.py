from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import GlossaryTerm

router = APIRouter(prefix="/api/glossary", tags=["glossary"])


class GlossaryInput(BaseModel):
    source_term: str = Field(min_length=1, max_length=255)
    target_term: str = Field(min_length=1, max_length=255)
    source_language: str = "auto"
    target_language: str = "hi"


@router.get("")
def list_glossary(db: Session = Depends(get_db)):
    return [{"id": term.id, "source_term": term.source_term, "target_term": term.target_term, "source_language": term.source_language, "target_language": term.target_language} for term in db.query(GlossaryTerm).order_by(GlossaryTerm.source_term).all()]


@router.post("", status_code=201)
def create_glossary(body: GlossaryInput, db: Session = Depends(get_db)):
    term = db.query(GlossaryTerm).filter_by(source_term=body.source_term).first()
    if term:
        term.target_term = body.target_term
        term.source_language = body.source_language
        term.target_language = body.target_language
    else:
        term = GlossaryTerm(**body.model_dump())
        db.add(term)
    db.commit()
    db.refresh(term)
    return {"id": term.id, **body.model_dump()}


@router.delete("/{term_id}")
def delete_glossary(term_id: int, db: Session = Depends(get_db)):
    term = db.get(GlossaryTerm, term_id)
    if not term:
        raise HTTPException(404, detail={"code": "GLOSSARY_TERM_NOT_FOUND", "message": "Glossary term not found."})
    db.delete(term)
    db.commit()
    return {"deleted": True}
