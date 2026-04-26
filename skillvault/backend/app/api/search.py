from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.search import RagAskRequest, SearchRequest
from app.services.rag_service import RagService

router = APIRouter(tags=["search"])


@router.post("/api/search")
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    rag = RagService(db)
    if payload.mode == "vector":
        chunks = rag.search_similar(payload.query, top_k=payload.top_k)
    else:
        chunks = rag.search_keyword(payload.query, top_k=payload.top_k)
    return [
        {
            "chunk_id": c.id,
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "content": c.content,
        }
        for c in chunks
    ]


@router.post("/api/rag/ask")
def rag_ask(payload: RagAskRequest, db: Session = Depends(get_db)):
    rag = RagService(db)
    return rag.ask(payload.question, top_k=payload.top_k)
