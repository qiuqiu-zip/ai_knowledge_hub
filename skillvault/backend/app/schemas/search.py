from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    mode: str = "keyword"
    top_k: int = 5


class RagAskRequest(BaseModel):
    question: str
    top_k: int = 5
