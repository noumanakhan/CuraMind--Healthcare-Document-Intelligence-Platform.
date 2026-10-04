from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class CitationItem(BaseModel):
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None
    snippet: Optional[str] = None


class ConversationCreate(BaseModel):
    patient_id: Optional[str] = None
    title: Optional[str] = "Clinical Assistant Session"


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    patient_id: Optional[str] = None
    user_id: str
    title: str
    created_at: str
    updated_at: str


class MessageCreate(BaseModel):
    content: str
    stream: Optional[bool] = False


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    citations: List[CitationItem] = []
    disclaimer: Optional[str] = (
        "Informational assistant output only. Requires licensed clinician review before any clinical action. "
        "Does not establish a diagnosis or autonomous treatment plan."
    )
    created_at: str
