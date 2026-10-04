from typing import List, Optional
from pydantic import BaseModel


class EvaluationCase(BaseModel):
    id: str
    patient_id: str
    question: str
    expected_answer_keywords: List[str]
    expected_source_documents: List[str]
    should_refuse: bool = False  # True if the information is not in the patient's records


class EvaluationResult(BaseModel):
    case_id: str
    question: str
    passed: bool
    grounded: bool
    refused_appropriately: bool
    citations_correct: bool
    actual_answer: str
    actual_citations: List[str]
    notes: Optional[str] = None


class EvaluationSummaryOut(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    accuracy_score: float
    groundedness_score: float
    results: List[EvaluationResult]
