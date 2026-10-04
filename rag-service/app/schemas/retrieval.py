from typing import List, Optional
from pydantic import BaseModel, Field


class SearchQueryRequest(BaseModel):
    query: str
    patient_id: Optional[str] = None
    top_k: Optional[int] = Field(default=8, ge=1, le=20)


class RetrievedChunkOut(BaseModel):
    id: str
    document_id: str
    document_name: str
    document_type: str
    workspace_id: str
    patient_id: str
    chunk_text: str
    page_number: Optional[int] = None
    chunk_index: int
    similarity: float
    distance: float


class SearchResponseOut(BaseModel):
    query: str
    workspace_id: str
    patient_id: Optional[str] = None
    total_results: int
    chunks: List[RetrievedChunkOut]
