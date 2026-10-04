from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ExtractedFieldIn(BaseModel):
    label: str
    value: str
    confidence: Optional[float] = 1.0
    flagged: Optional[bool] = False


class ExtractedFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    workspace_id: str
    label: str
    value: str
    confidence: float
    flagged: bool
    confirmed: bool
    created_at: Optional[str] = None


class DocumentCreate(BaseModel):
    patient_id: str
    name: str
    type: str  # "lab_report", "clinical_note", "intake_form", "discharge_summary"
    date: Optional[str] = None
    source: Optional[str] = "upload"
    full_text: Optional[str] = None
    fields: Optional[List[ExtractedFieldIn]] = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    patient_id: str
    name: str
    type: str
    date: Optional[str] = None
    status: str
    processing_error: Optional[str] = None
    full_text: Optional[str] = None
    source: Optional[str] = None
    is_deleted: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    extracted_fields: Optional[List[ExtractedFieldOut]] = None


class DocumentChunkOut(BaseModel):
    id: str
    document_id: str
    workspace_id: str
    patient_id: str
    chunk_text: str
    page_number: Optional[int] = None
    chunk_index: int
    created_at: Optional[str] = None
