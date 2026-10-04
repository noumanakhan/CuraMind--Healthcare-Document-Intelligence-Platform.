import pytest
from app.core.rbac import AuthenticatedUser
from app.db import postgres as db
from app.schemas.evaluation import EvaluationCase
from app.services.evaluation import run_evaluation_benchmark
from app.services.ingestion import process_document_background
from tests.conftest import auth_header, make_token


@pytest.mark.anyio
async def test_evaluation_benchmark_runner():
    ws_id = "ws-eval-1"
    user = AuthenticatedUser(id="admin-eval", workspace_id=ws_id, role="admin")

    # Ingest document for patient p1
    await db.insert_document({
        "id": "doc-eval-p1",
        "workspace_id": ws_id,
        "patient_id": "p1",
        "name": "Intake Form",
        "type": "intake_form",
    })
    await process_document_background(
        doc_id="doc-eval-p1",
        workspace_id=ws_id,
        patient_id="p1",
        file_bytes=b"Admission Blood Pressure: 140/90 mmHg. Primary Complaint: Severe cough and hypertension.",
        filename="Intake Form.txt",
        user_id=user.id,
    )

    test_cases = [
        EvaluationCase(
            id="test-eval-1",
            patient_id="p1",
            question="What was the patient's admission blood pressure?",
            expected_answer_keywords=["blood pressure", "140", "90"],
            expected_source_documents=["Intake Form"],
            should_refuse=False,
        ),
        EvaluationCase(
            id="test-eval-2",
            patient_id="p1",
            question="What is the patient's favorite football team?",
            expected_answer_keywords=["no relevant", "not found"],
            expected_source_documents=[],
            should_refuse=True,
        ),
    ]

    summary = await run_evaluation_benchmark(workspace_id=ws_id, user=user, cases=test_cases)
    assert summary.total_cases == 2
    assert summary.passed_cases == 2
    assert summary.accuracy_score == 100.0
    assert summary.groundedness_score == 100.0


def test_evaluation_api_endpoint(client):
    admin_token = make_token("u-admin", "ws-eval-api", "admin")
    res = client.post("/api/v1/evaluation/run", headers=auth_header(admin_token))
    assert res.status_code == 200
    data = res.json()
    assert data["total_cases"] >= 16
    assert data["accuracy_score"] >= 90.0
