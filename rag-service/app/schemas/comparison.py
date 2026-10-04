from typing import List, Optional
from pydantic import BaseModel


class DocumentCompareRequest(BaseModel):
    doc1_id: str
    doc2_id: str
    mode: Optional[str] = "both"  # "structured" | "full_text" | "both"


class StructuredFieldDiff(BaseModel):
    label: str
    doc1_value: Optional[str] = None
    doc2_value: Optional[str] = None
    status: str  # "matched" | "differ" | "only_in_doc1" | "only_in_doc2"


class TextDiffSection(BaseModel):
    tag: str  # "equal" | "replace" | "delete" | "insert"
    doc1_lines: List[str]
    doc2_lines: List[str]
    doc1_page: Optional[int] = None
    doc2_page: Optional[int] = None


class DocumentComparisonResponse(BaseModel):
    doc1_id: str
    doc1_name: str
    doc2_id: str
    doc2_name: str
    workspace_id: str
    patient_id: str
    structured_diffs: List[StructuredFieldDiff]
    text_diffs: List[TextDiffSection]
    summary: str
    total_differences_count: int
