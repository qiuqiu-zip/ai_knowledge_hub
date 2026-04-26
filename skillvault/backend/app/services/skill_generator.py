from sqlalchemy.orm import Session

from app.db import models
from app.services.llm_service import LLMService


class SkillGeneratorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm = LLMService()

    def generate_from_document(self, doc: models.SourceDocument) -> models.SkillCandidate:
        payload = self.llm.generate_skill_candidate(
            text=doc.content,
            source_metadata={"title": doc.title, "source_url": doc.source_url, "license": doc.license},
        )
        candidate = self.db.query(models.SkillCandidate).filter(
            models.SkillCandidate.source_document_id == doc.id,
            models.SkillCandidate.status == models.CandidateStatus.draft,
        ).first()
        if not candidate:
            candidate = models.SkillCandidate(source_document_id=doc.id, title=doc.title, prompt_template="")
            self.db.add(candidate)

        candidate.title = payload.get("title") or doc.title
        candidate.scenario = payload.get("scenario")
        candidate.input_schema = payload.get("input_schema") or {}
        candidate.prompt_template = payload.get("prompt_template") or ""
        candidate.output_format = payload.get("output_format")
        candidate.examples = payload.get("examples") or []
        candidate.tags = payload.get("tags") or []
        candidate.source_url = doc.source_url
        candidate.license = doc.license
        candidate.status = models.CandidateStatus.draft
        self.db.flush()
        return candidate
