import os
import tempfile

TEST_DATABASE = os.path.join(tempfile.gettempdir(), "curamind-clinical-tests.sqlite3")
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///" + TEST_DATABASE
os.environ["JWT_SECRET"] = "test-secret-with-more-than-thirty-two-characters"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["ALLOW_PUBLIC_REGISTRATION"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models import (
    Appointment,
    AuditEvent,
    DischargeDraft,
    Document,
    ExtractedField,
    Patient,
    User,
    Workspace,
)

TEST_ENGINE = create_engine("sqlite:///" + TEST_DATABASE, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db, workspace_name, email, role):
    ws = db.query(Workspace).filter(Workspace.name == workspace_name).first()
    if not ws:
        ws = Workspace(name=workspace_name)
        db.add(ws)
        db.flush()
    user = User(
        workspace_id=ws.id,
        email=email,
        name=f"User {role}",
        password_hash=hash_password("test-password-1234"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, ws.id, role)
    return user, ws, {"Authorization": f"Bearer {token}"}


def test_workspace_isolation_for_all_entities(client):
    db = TestSession()
    u1, ws1, h1 = make_user(db, "Hospital One", "admin1@h1.com", "admin")
    u2, ws2, h2 = make_user(db, "Hospital Two", "admin2@h2.com", "admin")

    # Admin 1 in WS1 creates patient
    res = client.post("/api/v1/patients", json={
        "name": "Jane Hospital1",
        "dob": "1990-01-01",
        "sex": "female",
    }, headers=h1)
    assert res.status_code == 201
    p1_id = res.json()["id"]

    # Admin 2 in WS2 cannot see patient in list or by ID
    res2_list = client.get("/api/v1/patients", headers=h2)
    assert res2_list.status_code == 200
    assert len(res2_list.json()["patients"]) == 0

    res2_get = client.get(f"/api/v1/patients/{p1_id}", headers=h2)
    assert res2_get.status_code == 404

    # Admin 2 cannot add document to patient in WS1
    res2_doc = client.post(f"/api/v1/patients/{p1_id}/documents", json={
        "name": "Infiltrate Note",
        "type": "clinical_note",
    }, headers=h2)
    assert res2_doc.status_code == 404

    # Admin 2 cannot get discharge summary of patient in WS1
    res2_discharge = client.get(f"/api/v1/patients/{p1_id}/discharge", headers=h2)
    assert res2_discharge.status_code == 404

    db.close()



def test_role_denials_and_allowances(client):
    db = TestSession()
    u_admin, ws, h_admin = make_user(db, "Main Hospital", "admin@main.com", "admin")
    u_clinician, _, h_clinician = make_user(db, "Main Hospital", "clinician@main.com", "clinician")
    u_records, _, h_records = make_user(db, "Main Hospital", "records@main.com", "records")
    u_viewer, _, h_viewer = make_user(db, "Main Hospital", "viewer@main.com", "viewer")

    # Viewer cannot create patient
    res_viewer_create = client.post("/api/v1/patients", json={
        "name": "Patient X",
        "dob": "1985-05-05",
        "sex": "male",
    }, headers=h_viewer)
    assert res_viewer_create.status_code == 403

    # Records CAN create patient
    res_records_create = client.post("/api/v1/patients", json={
        "name": "Patient Valid",
        "dob": "1985-05-05",
        "sex": "male",
        "allergies": ["Penicillin"],
    }, headers=h_records)
    assert res_records_create.status_code == 201
    patient_id = res_records_create.json()["id"]

    # Clinician uploads document with an extracted field
    doc_res = client.post(f"/api/v1/patients/{patient_id}/documents", json={
        "name": "Consult Report",
        "type": "clinical_note",
        "fields": [{"label": "Diagnosis", "value": "Asthma", "confidence": 0.95}],
    }, headers=h_clinician)
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]
    field_id = doc_res.json()["extracted_fields"][0]["id"]

    # Viewer cannot confirm field
    confirm_viewer = client.patch(f"/api/v1/documents/{doc_id}/fields/{field_id}/confirm", headers=h_viewer)
    assert confirm_viewer.status_code == 403

    # Records cannot confirm field
    confirm_records = client.patch(f"/api/v1/documents/{doc_id}/fields/{field_id}/confirm", headers=h_records)
    assert confirm_records.status_code == 403

    # Clinician CAN confirm field
    confirm_clinician = client.patch(f"/api/v1/documents/{doc_id}/fields/{field_id}/confirm", headers=h_clinician)
    assert confirm_clinician.status_code == 200
    assert confirm_clinician.json()["confirmed_by_id"] == u_clinician.id

    # Records cannot view clinical chart / discharge
    discharge_records = client.get(f"/api/v1/patients/{patient_id}/discharge", headers=h_records)
    assert discharge_records.status_code == 403

    # Records cannot sign discharge
    sign_records = client.post(f"/api/v1/patients/{patient_id}/discharge/sign", headers=h_records)
    assert sign_records.status_code == 403

    # Clinician CAN view and sign discharge
    discharge_clinician = client.get(f"/api/v1/patients/{patient_id}/discharge", headers=h_clinician)
    assert discharge_clinician.status_code == 200
    assert discharge_clinician.json()["status"] == "draft"

    sign_clinician = client.post(f"/api/v1/patients/{patient_id}/discharge/sign", headers=h_clinician)
    assert sign_clinician.status_code == 200
    assert sign_clinician.json()["status"] == "signed"

    db.close()


def test_idempotency_conflicts(client):
    db = TestSession()
    u_admin, ws, h_admin = make_user(db, "Clinic A", "admin@clinica.com", "admin")
    u_doc, _, h_doc = make_user(db, "Clinic A", "doc@clinica.com", "clinician")

    # Create patient and document
    p_res = client.post("/api/v1/patients", json={
        "name": "Idempotent Patient",
        "dob": "1992-02-02",
        "sex": "female",
    }, headers=h_admin)
    assert p_res.status_code == 201
    p = p_res.json()

    doc_res = client.post(f"/api/v1/patients/{p['id']}/documents", json={
        "name": "Discharge Note",
        "type": "discharge_summary",
        "fields": [{"label": "Followup", "value": "2 weeks"}],
    }, headers=h_doc)
    assert doc_res.status_code == 201
    doc = doc_res.json()

    field_id = doc["extracted_fields"][0]["id"]

    # First confirmation succeeds
    r1 = client.patch(f"/api/v1/documents/{doc['id']}/fields/{field_id}/confirm", headers=h_doc)
    assert r1.status_code == 200

    # Second confirmation returns 409
    r2 = client.patch(f"/api/v1/documents/{doc['id']}/fields/{field_id}/confirm", headers=h_doc)
    assert r2.status_code == 409

    # First discharge sign succeeds
    s1 = client.post(f"/api/v1/patients/{p['id']}/discharge/sign", headers=h_doc)
    assert s1.status_code == 200

    # Second discharge sign returns 409
    s2 = client.post(f"/api/v1/patients/{p['id']}/discharge/sign", headers=h_doc)
    assert s2.status_code == 409

    db.close()



def test_soft_delete_patient(client):
    db = TestSession()
    u, ws, h_admin = make_user(db, "Clinic B", "admin@clinicb.com", "admin")

    p = client.post("/api/v1/patients", json={
        "name": "Delete Me",
        "dob": "1970-01-01",
        "sex": "other",
    }, headers=h_admin).json()
    p_id = p["id"]

    # Active patient in list
    res_list = client.get("/api/v1/patients", headers=h_admin).json()
    assert any(x["id"] == p_id for x in res_list["patients"])

    # Soft delete patient
    del_res = client.patch(f"/api/v1/patients/{p_id}", json={"is_deleted": True}, headers=h_admin)
    assert del_res.status_code == 200

    # Excluded from active list
    res_list_after = client.get("/api/v1/patients", headers=h_admin).json()
    assert not any(x["id"] == p_id for x in res_list_after["patients"])

    # Excluded from standard GET /patients/{id}
    assert client.get(f"/api/v1/patients/{p_id}", headers=h_admin).status_code == 404

    # Exists in raw database
    raw_p = db.query(Patient).filter(Patient.id == p_id).first()
    assert raw_p is not None
    assert raw_p.is_deleted is True

    db.close()


def test_audit_events_created_for_clinical_mutations(client):
    db = TestSession()
    u_admin, ws, h_admin = make_user(db, "Audit Hospital", "admin@audithosp.com", "admin")
    u_records, _, h_records = make_user(db, "Audit Hospital", "records@audithosp.com", "records")
    u_clinician, _, h_clinician = make_user(db, "Audit Hospital", "doc@audithosp.com", "clinician")

    # 1. Create Patient
    p_res = client.post("/api/v1/patients", json={
        "name": "Audit Tracked Patient",
        "dob": "2000-01-01",
        "sex": "female",
    }, headers=h_records)
    p_id = p_res.json()["id"]

    # 2. Upload Document & Confirm Field
    doc = client.post(f"/api/v1/patients/{p_id}/documents", json={
        "name": "Lab Form",
        "type": "lab_report",
        "fields": [{"label": "WBC", "value": "7.5"}],
    }, headers=h_clinician).json()
    field_id = doc["extracted_fields"][0]["id"]
    client.patch(f"/api/v1/documents/{doc['id']}/fields/{field_id}/confirm", headers=h_clinician)

    # 3. Schedule Appointment
    client.post(f"/api/v1/patients/{p_id}/appointments", json={
        "type": "Cardiology Follow-up",
        "with_provider_name": "Dr. Smith",
        "date": "2026-11-01",
        "time": "14:00",
    }, headers=h_records)

    # 4. Sign Discharge
    client.post(f"/api/v1/patients/{p_id}/discharge/sign", headers=h_clinician)

    # Fetch audit log for patient (admin only)
    audit_res = client.get(f"/api/v1/patients/{p_id}/audit", headers=h_admin)
    assert audit_res.status_code == 200
    events = audit_res.json()["events"]
    actions = [e["action"] for e in events]

    assert "patient.created" in actions
    assert "document.uploaded" in actions
    assert "document.field_confirmed" in actions
    assert "appointment.scheduled" in actions
    assert "discharge.signed" in actions

    # Check non-admin cannot view audit log
    assert client.get(f"/api/v1/patients/{p_id}/audit", headers=h_clinician).status_code == 403

    db.close()
