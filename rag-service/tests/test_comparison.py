import pytest
from app.db import postgres as db
from app.services.comparison import compare_documents
from tests.conftest import auth_header, make_token


@pytest.mark.anyio
async def test_deterministic_comparison_structured_and_text():
    ws_id = "ws-comp-1"
    pat_id = "p-comp-1"

    # Create Doc 1
    await db.insert_document({
        "id": "doc-cmp-1",
        "workspace_id": ws_id,
        "patient_id": pat_id,
        "name": "Consultation Day 1",
        "type": "clinical_note",
        "full_text": "Diagnosis: Acute Bronchitis.\nTreatment: Rest and hydration.\nFollow-up: 7 days."
    })
    await db.insert_extracted_field({
        "document_id": "doc-cmp-1",
        "workspace_id": ws_id,
        "label": "Chief Complaint",
        "value": "Persistent dry cough",
    })
    await db.insert_extracted_field({
        "document_id": "doc-cmp-1",
        "workspace_id": ws_id,
        "label": "Suggested ICD-10",
        "value": "J20.9",
    })

    # Create Doc 2 (Modified values)
    await db.insert_document({
        "id": "doc-cmp-2",
        "workspace_id": ws_id,
        "patient_id": pat_id,
        "name": "Consultation Day 5",
        "type": "clinical_note",
        "full_text": "Diagnosis: Resolved Bronchitis.\nTreatment: Patient discharged home.\nFollow-up: As needed."
    })
    await db.insert_extracted_field({
        "document_id": "doc-cmp-2",
        "workspace_id": ws_id,
        "label": "Chief Complaint",
        "value": "Cough resolving, mild fatigue",
    })
    await db.insert_extracted_field({
        "document_id": "doc-cmp-2",
        "workspace_id": ws_id,
        "label": "Suggested ICD-10",
        "value": "J20.9",  # Matched
    })
    await db.insert_extracted_field({
        "document_id": "doc-cmp-2",
        "workspace_id": ws_id,
        "label": "Discharge Status",
        "value": "Discharged home",  # only_in_doc2
    })

    res = await compare_documents("doc-cmp-1", "doc-cmp-2", workspace_id=ws_id)
    assert res.total_differences_count > 0
    assert len(res.structured_diffs) == 3

    # Check Chief Complaint differed
    cc_diff = next(d for d in res.structured_diffs if d.label == "Chief Complaint")
    assert cc_diff.status == "differ"

    # Check ICD-10 matched
    icd_diff = next(d for d in res.structured_diffs if d.label == "Suggested ICD-10")
    assert icd_diff.status == "matched"

    # Check Discharge Status only in doc 2
    ds_diff = next(d for d in res.structured_diffs if d.label == "Discharge Status")
    assert ds_diff.status == "only_in_doc2"


def test_cross_workspace_comparison_rejected(client):
    token_ws1 = make_token("u1", "ws-1", "clinician")

    # Request comparing doc in ws-1 with doc in ws-2
    res = client.post(
        "/api/v1/patients/p1/documents/compare",
        json={"doc1_id": "doc-ws1", "doc2_id": "doc-ws2"},
        headers=auth_header(token_ws1),
    )
    assert res.status_code == 404
