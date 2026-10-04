import logging
from typing import List, Optional
from app.core.rbac import AuthenticatedUser
from app.db import postgres as db
from app.schemas.evaluation import EvaluationCase, EvaluationResult, EvaluationSummaryOut
from app.services.ingestion import process_document_background
from app.services.rag_assistant import ask_rag_assistant

logger = logging.getLogger("rag_service.evaluation")

# Standard 16-case clinical benchmark test set
EVALUATION_BENCHMARK_CASES: List[EvaluationCase] = [
    EvaluationCase(
        id="eval-01",
        patient_id="p1",
        question="What was the patient's admission blood pressure and primary complaint?",
        expected_answer_keywords=["blood pressure", "complaint", "hypertension", "140", "90"],
        expected_source_documents=["Intake Form", "intake-form-amina-yusuf.pdf"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-02",
        patient_id="p1",
        question="Which antibiotics was the patient prescribed for pneumonia?",
        expected_answer_keywords=["amoxicillin", "azithromycin", "antibiotic"],
        expected_source_documents=["Clinical Note", "discharge-summary.pdf"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-03",
        patient_id="p1",
        question="What were the hemoglobin levels on the latest complete blood count?",
        expected_answer_keywords=["hemoglobin", "g/dl", "11.2", "12"],
        expected_source_documents=["Lab Report", "lab-cbc-panel.pdf"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-04",
        patient_id="p1",
        question="Did the patient undergo brain surgery during this admission?",
        expected_answer_keywords=["no relevant", "not found"],
        expected_source_documents=[],
        should_refuse=True,
    ),
    EvaluationCase(
        id="eval-05",
        patient_id="p1",
        question="What are the patient's verified drug allergies?",
        expected_answer_keywords=["penicillin", "allergy", "allergies", "sulfa"],
        expected_source_documents=["Intake Form", "clinical_note"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-06",
        patient_id="p2",
        question="What was the reason for the cardiology consultation on 26 Sep 2026?",
        expected_answer_keywords=["chest pain", "cardiology", "exertional"],
        expected_source_documents=["Consultation Note", "cardio_consult.pdf"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-07",
        patient_id="p2",
        question="What is the patient's dose of Metoprolol?",
        expected_answer_keywords=["metoprolol", "25mg", "50mg", "daily", "oral"],
        expected_source_documents=["Medication List", "cardio_consult.pdf"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-08",
        patient_id="p2",
        question="What was the patient's pediatric vaccination record in 1980?",
        expected_answer_keywords=["no relevant", "not found"],
        expected_source_documents=[],
        should_refuse=True,
    ),
    EvaluationCase(
        id="eval-09",
        patient_id="p3",
        question="What was the patient's fasting glucose reading on admission?",
        expected_answer_keywords=["glucose", "mg/dl", "fasting"],
        expected_source_documents=["Lab Report"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-10",
        patient_id="p3",
        question="What discharge instructions were provided regarding wound care?",
        expected_answer_keywords=["wound", "dressing", "clean", "discharge"],
        expected_source_documents=["Discharge Summary"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-11",
        patient_id="p3",
        question="What brand of eyeglasses does the patient wear?",
        expected_answer_keywords=["no relevant", "not found"],
        expected_source_documents=[],
        should_refuse=True,
    ),
    EvaluationCase(
        id="eval-12",
        patient_id="p4",
        question="What were the ICU vital trends over the past 24 hours?",
        expected_answer_keywords=["heart rate", "spo2", "temperature", "blood pressure"],
        expected_source_documents=["ICU Flowsheet"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-13",
        patient_id="p4",
        question="What is the mechanical ventilation weaning plan?",
        expected_answer_keywords=["weaning", "ventilation", "extubation", "cpap", "pressure support"],
        expected_source_documents=["Critical Care Progress Note"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-14",
        patient_id="p4",
        question="What is the patient's favorite vacation destination?",
        expected_answer_keywords=["no relevant", "not found"],
        expected_source_documents=[],
        should_refuse=True,
    ),
    EvaluationCase(
        id="eval-15",
        patient_id="p1",
        question="Has the discharge summary been signed by the attending physician?",
        expected_answer_keywords=["discharge", "signed", "attending", "physician"],
        expected_source_documents=["Discharge Summary"],
        should_refuse=False,
    ),
    EvaluationCase(
        id="eval-16",
        patient_id="p2",
        question="What follow-up echocardiogram schedule was recommended?",
        expected_answer_keywords=["echocardiogram", "follow-up", "weeks", "months"],
        expected_source_documents=["Cardiology Note"],
        should_refuse=False,
    ),
]


async def seed_benchmark_workspace(workspace_id: str, user_id: str):
    """Seeds standard clinical documents for patients p1, p2, p3, p4 if not present."""
    existing = await db.list_documents(workspace_id)
    if existing:
        return

    seed_docs = [
        ("doc-seed-p1-1", "p1", "intake-form-amina-yusuf.pdf", "intake_form", b"Admission Blood Pressure: 140/90 mmHg. Primary Complaint: Severe cough and hypertension. Known Penicillin allergy."),
        ("doc-seed-p1-2", "p1", "discharge-summary.pdf", "discharge_summary", b"Patient diagnosed with bacterial pneumonia. Prescribed Azithromycin 500mg daily. Discharge summary signed by attending physician."),
        ("doc-seed-p1-3", "p1", "lab-cbc-panel.pdf", "lab_report", b"Complete Blood Count: Hemoglobin 11.2 g/dL, Platelets 240,000, WBC 9.5."),
        ("doc-seed-p2-1", "p2", "cardio_consult.pdf", "clinical_note", b"Cardiology consultation for exertional chest pain on 26 Sep 2026. Prescribed Metoprolol 25mg daily oral. Follow-up echocardiogram in 4 weeks."),
        ("doc-seed-p3-1", "p3", "lab_glucose_report.pdf", "lab_report", b"Fasting blood glucose 118 mg/dL. Wound care instructions: keep surgical incision dry and clean daily."),
        ("doc-seed-p4-1", "p4", "icu_flowsheet.pdf", "clinical_note", b"ICU Flowsheet: Heart Rate 88 bpm, SpO2 96%, Temperature 37.1 C, Blood Pressure 118/76. Mechanical ventilation weaning plan initiated with CPAP/pressure support mode."),
    ]

    for doc_id, pat_id, name, doc_type, content in seed_docs:
        await db.insert_document({
            "id": doc_id,
            "workspace_id": workspace_id,
            "patient_id": pat_id,
            "name": name,
            "type": doc_type,
            "status": "processing",
        })
        await process_document_background(
            doc_id=doc_id,
            workspace_id=workspace_id,
            patient_id=pat_id,
            file_bytes=content,
            filename=name,
            user_id=user_id,
        )


async def run_evaluation_benchmark(
    workspace_id: str,
    user: AuthenticatedUser,
    cases: Optional[List[EvaluationCase]] = None,
) -> EvaluationSummaryOut:
    """
    Executes the clinical evaluation benchmark suite and returns groundedness and citation scores.
    """
    await seed_benchmark_workspace(workspace_id, user.id)

    eval_cases = cases or EVALUATION_BENCHMARK_CASES
    results: List[EvaluationResult] = []
    passed_count = 0

    for case in eval_cases:
        conv = await db.create_conversation({
            "workspace_id": workspace_id,
            "patient_id": case.patient_id,
            "user_id": user.id,
            "title": f"Eval: {case.id}",
        })

        msg_out = await ask_rag_assistant(
            conversation_id=conv["id"],
            user_query=case.question,
            user=user,
            patient_id=case.patient_id,
        )

        ans_lower = msg_out.content.lower()
        actual_citations = [c.document_name for c in msg_out.citations]

        if case.should_refuse:
            refused_appropriately = "no relevant" in ans_lower or "not found" in ans_lower
            grounded = len(msg_out.citations) == 0 or refused_appropriately
            citations_correct = True
            passed = refused_appropriately and grounded
        else:
            refused_appropriately = False
            has_keywords = any(kw.lower() in ans_lower for kw in case.expected_answer_keywords)
            has_citations = len(msg_out.citations) > 0
            grounded = has_citations
            citations_correct = len(msg_out.citations) > 0
            passed = has_keywords or has_citations

        if passed:
            passed_count += 1

        results.append(EvaluationResult(
            case_id=case.id,
            question=case.question,
            passed=passed,
            grounded=grounded,
            refused_appropriately=refused_appropriately if case.should_refuse else True,
            citations_correct=citations_correct,
            actual_answer=msg_out.content[:150] + ("..." if len(msg_out.content) > 150 else ""),
            actual_citations=actual_citations,
        ))

    accuracy = round((passed_count / len(eval_cases)) * 100.0, 2)
    groundedness = round((sum(1 for r in results if r.grounded) / len(eval_cases)) * 100.0, 2)

    return EvaluationSummaryOut(
        total_cases=len(eval_cases),
        passed_cases=passed_count,
        failed_cases=len(eval_cases) - passed_count,
        accuracy_score=accuracy,
        groundedness_score=groundedness,
        results=results,
    )
