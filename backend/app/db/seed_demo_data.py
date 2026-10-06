"""
Seed demo data for CuraMind application database.
Populates patients, document vault, extracted fields, appointments, medications,
labs, vitals, immunizations, discharge drafts, and audit logs.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import (
    Allergy,
    Appointment,
    AuditEvent,
    DischargeDraft,
    DischargeParagraph,
    Document,
    ExtractedField,
    Immunization,
    LabResultPoint,
    LabTest,
    Medication,
    Patient,
    User,
    Vitals,
    Workspace,
)

settings = get_settings()


def seed_demo_clinical_data(db: Session):
    # 1. Ensure Workspace
    workspace = db.query(Workspace).filter(Workspace.name == settings.default_workspace_name).first()
    if not workspace:
        workspace = Workspace(name=settings.default_workspace_name)
        db.add(workspace)
        db.flush()

    # 2. Ensure Users
    users = {}
    user_specs = [
        ("admin@gmail.com", "Admin", "admin", "allahmuhammad"),
        ("admin@curamind.local", "Dr. N. Fatima (Admin)", "admin", "Admin12345678!"),
        ("dr.faisal@curamind.local", "Dr. Faisal S.", "clinician", "Doctor12345678!"),
        ("records@curamind.local", "Nurse R. Bibi", "records", "Records12345678!"),
    ]

    for email, name, role, pwd in user_specs:
        u = db.query(User).filter(User.workspace_id == workspace.id, User.email == email).first()
        if not u:
            u = User(
                workspace_id=workspace.id,
                email=email,
                name=name,
                password_hash=hash_password(pwd),
                role=role,
                is_active=True,
            )
            db.add(u)
            db.flush()
        users[email] = u

    admin_user = users["admin@gmail.com"]
    clinician_user = users["dr.faisal@curamind.local"]

    # 3. Check if patients already seeded
    existing_patient_count = db.query(Patient).filter(Patient.workspace_id == workspace.id).count()
    if existing_patient_count > 0:
        print(f"[*] Database already contains {existing_patient_count} patients. Skipping seed.")
        return

    now = datetime.now(timezone.utc)

    # 4. Create Patients
    p1 = Patient(
        id="p1",
        workspace_id=workspace.id,
        mrn="MRN-88213",
        name="Amina Yusuf",
        dob="14 Mar 1988",
        sex="Female",
        blood_type="O+",
        phone="0300-1234567",
        email="amina.yusuf@example.com",
        address="House 12, Street 4, Gulberg, Lahore",
        emergency_contact="Zainab Yusuf (Sister) · 0300-7654321",
        insurance_provider="State Life Health",
        policy_number="SLH-44219-A",
        attending_physician_id=clinician_user.id,
        ward="Internal Medicine · Bed 4B",
        status="admitted",
        created_by_id=admin_user.id,
    )

    p2 = Patient(
        id="p2",
        workspace_id=workspace.id,
        mrn="MRN-77190",
        name="Hassan Raza",
        dob="02 Nov 1965",
        sex="Male",
        blood_type="A+",
        phone="0321-9988776",
        email="hassan.raza@example.com",
        address="Flat 6B, DHA Phase 5, Karachi",
        emergency_contact="Bilal Raza (Son) · 0321-1122334",
        insurance_provider="Jubilee Health Insurance",
        policy_number="JHI-88012-B",
        attending_physician_id=admin_user.id,
        ward="Cardiology · Bed 1A",
        status="discharge_pending",
        created_by_id=admin_user.id,
    )

    p3 = Patient(
        id="p3",
        workspace_id=workspace.id,
        mrn="MRN-90344",
        name="Layla Ahmed",
        dob="29 Jul 2001",
        sex="Female",
        blood_type="B-",
        phone="0333-4455667",
        email="layla.ahmed@example.com",
        address="House 88, Model Town, Lahore",
        emergency_contact="Ahmed Raza (Father) · 0333-7788990",
        insurance_provider="Self-pay",
        policy_number="—",
        attending_physician_id=clinician_user.id,
        ward="Outpatient",
        status="discharged",
        created_by_id=admin_user.id,
    )

    p4 = Patient(
        id="p4",
        workspace_id=workspace.id,
        mrn="MRN-65521",
        name="Omar Siddiqui",
        dob="18 Jan 1979",
        sex="Male",
        blood_type="AB+",
        phone="0345-2233445",
        email="omar.siddiqui@example.com",
        address="House 21, F-10, Islamabad",
        emergency_contact="Sana Siddiqui (Wife) · 0345-5566778",
        insurance_provider="EFU Health",
        policy_number="EFU-30291-C",
        attending_physician_id=admin_user.id,
        ward="ICU · Bed 2",
        status="admitted",
        created_by_id=admin_user.id,
    )

    db.add_all([p1, p2, p3, p4])
    db.flush()

    # 5. Allergies
    allergies = [
        Allergy(patient_id=p1.id, allergen="Penicillin", noted_by_id=clinician_user.id),
        Allergy(patient_id=p3.id, allergen="Sulfa drugs", noted_by_id=clinician_user.id),
        Allergy(patient_id=p3.id, allergen="Latex", noted_by_id=clinician_user.id),
    ]
    db.add_all(allergies)

    # 6. Vitals
    vitals = [
        Vitals(patient_id=p1.id, workspace_id=workspace.id, bp="118/76", hr=92, temp=38.1, spo2=97, weight=61.0, recorded_by_id=clinician_user.id),
        Vitals(patient_id=p2.id, workspace_id=workspace.id, bp="132/84", hr=78, temp=36.8, spo2=98, weight=84.0, recorded_by_id=admin_user.id),
        Vitals(patient_id=p3.id, workspace_id=workspace.id, bp="110/70", hr=72, temp=36.6, spo2=99, weight=58.0, recorded_by_id=clinician_user.id),
        Vitals(patient_id=p4.id, workspace_id=workspace.id, bp="128/82", hr=91, temp=37.4, spo2=96, weight=76.0, recorded_by_id=admin_user.id),
    ]
    db.add_all(vitals)

    # 7. Immunizations
    immunizations = [
        Immunization(patient_id=p1.id, workspace_id=workspace.id, vaccine_name="Tetanus (Td)", administered_date="12 Jan 2024", recorded_by_id=clinician_user.id),
        Immunization(patient_id=p1.id, workspace_id=workspace.id, vaccine_name="Influenza", administered_date="03 Oct 2025", recorded_by_id=clinician_user.id),
        Immunization(patient_id=p2.id, workspace_id=workspace.id, vaccine_name="Influenza", administered_date="15 Nov 2025", recorded_by_id=admin_user.id),
        Immunization(patient_id=p2.id, workspace_id=workspace.id, vaccine_name="Pneumococcal", administered_date="20 Mar 2023", recorded_by_id=admin_user.id),
        Immunization(patient_id=p3.id, workspace_id=workspace.id, vaccine_name="HPV (3rd dose)", administered_date="08 Feb 2022", recorded_by_id=clinician_user.id),
        Immunization(patient_id=p3.id, workspace_id=workspace.id, vaccine_name="Hepatitis B series", administered_date="14 May 2023", recorded_by_id=clinician_user.id),
        Immunization(patient_id=p4.id, workspace_id=workspace.id, vaccine_name="Tetanus (Td)", administered_date="19 Jun 2025", recorded_by_id=admin_user.id),
    ]
    db.add_all(immunizations)

    # 8. Medications
    meds = [
        Medication(patient_id=p1.id, workspace_id=workspace.id, name="Amoxicillin 500mg", dose="3x daily", flag="interaction", flag_note="Patient has a documented penicillin allergy — cross-reactivity risk."),
        Medication(patient_id=p1.id, workspace_id=workspace.id, name="Paracetamol 1g", dose="As needed", flag=None),
        Medication(patient_id=p2.id, workspace_id=workspace.id, name="Atorvastatin 40mg", dose="Nightly", flag=None),
        Medication(patient_id=p2.id, workspace_id=workspace.id, name="Aspirin 75mg", dose="Daily", flag=None),
        Medication(patient_id=p2.id, workspace_id=workspace.id, name="Metoprolol 50mg", dose="2x daily", flag="dosage", flag_note="Dose is above the typical starting range for this patient’s renal function — confirm with prescriber."),
        Medication(patient_id=p3.id, workspace_id=workspace.id, name="Omeprazole 20mg", dose="Once daily before breakfast", flag=None, flag_note="Prescribed at discharge for functional dyspepsia (4-week course pending GI review)."),
        Medication(patient_id=p4.id, workspace_id=workspace.id, name="Piperacillin-Tazobactam", dose="4.5g IV, 3x daily", flag=None),
        Medication(patient_id=p4.id, workspace_id=workspace.id, name="Norepinephrine infusion", dose="Titrated", flag=None),
    ]
    db.add_all(meds)

    # 9. Lab Tests & Result Points
    lab_wbc = LabTest(patient_id=p1.id, workspace_id=workspace.id, test_name="White Blood Cell Count", unit="x10⁹/L", reference_low=4.0, reference_high=11.0)
    lab_crp = LabTest(patient_id=p1.id, workspace_id=workspace.id, test_name="C-Reactive Protein", unit="mg/L", reference_low=0.0, reference_high=10.0)
    lab_ldl = LabTest(patient_id=p2.id, workspace_id=workspace.id, test_name="LDL Cholesterol", unit="mg/dL", reference_low=0.0, reference_high=100.0)
    lab_hgb = LabTest(patient_id=p3.id, workspace_id=workspace.id, test_name="Hemoglobin", unit="g/dL", reference_low=12.0, reference_high=15.5)
    lab_ferritin = LabTest(patient_id=p3.id, workspace_id=workspace.id, test_name="Serum Ferritin", unit="ng/mL", reference_low=15.0, reference_high=150.0)
    lab_lactate = LabTest(patient_id=p4.id, workspace_id=workspace.id, test_name="Lactate", unit="mmol/L", reference_low=0.5, reference_high=2.2)

    db.add_all([lab_wbc, lab_crp, lab_ldl, lab_hgb, lab_ferritin, lab_lactate])
    db.flush()

    points = [
        LabResultPoint(lab_test_id=lab_wbc.id, value=8.1, recorded_at=now - timedelta(days=5)),
        LabResultPoint(lab_test_id=lab_wbc.id, value=9.6, recorded_at=now - timedelta(days=3)),
        LabResultPoint(lab_test_id=lab_wbc.id, value=12.1, recorded_at=now - timedelta(days=1)),
        LabResultPoint(lab_test_id=lab_wbc.id, value=13.4, recorded_at=now),
        LabResultPoint(lab_test_id=lab_crp.id, value=6.0, recorded_at=now - timedelta(days=5)),
        LabResultPoint(lab_test_id=lab_crp.id, value=14.0, recorded_at=now - timedelta(days=3)),
        LabResultPoint(lab_test_id=lab_crp.id, value=27.0, recorded_at=now - timedelta(days=1)),
        LabResultPoint(lab_test_id=lab_crp.id, value=38.0, recorded_at=now),
        LabResultPoint(lab_test_id=lab_ldl.id, value=142.0, recorded_at=now - timedelta(days=15)),
        LabResultPoint(lab_test_id=lab_ldl.id, value=128.0, recorded_at=now - timedelta(days=7)),
        LabResultPoint(lab_test_id=lab_ldl.id, value=109.0, recorded_at=now - timedelta(days=1)),
        LabResultPoint(lab_test_id=lab_hgb.id, value=13.2, recorded_at=now - timedelta(days=10)),
        LabResultPoint(lab_test_id=lab_hgb.id, value=12.9, recorded_at=now - timedelta(days=3)),
        LabResultPoint(lab_test_id=lab_hgb.id, value=12.8, recorded_at=now - timedelta(days=2)),
        LabResultPoint(lab_test_id=lab_ferritin.id, value=48.0, recorded_at=now - timedelta(days=10)),
        LabResultPoint(lab_test_id=lab_ferritin.id, value=44.0, recorded_at=now - timedelta(days=3)),
        LabResultPoint(lab_test_id=lab_lactate.id, value=3.1, recorded_at=now - timedelta(days=2)),
        LabResultPoint(lab_test_id=lab_lactate.id, value=2.4, recorded_at=now - timedelta(days=1)),
        LabResultPoint(lab_test_id=lab_lactate.id, value=1.8, recorded_at=now),
    ]
    db.add_all(points)

    # 10. Appointments
    appts = [
        Appointment(patient_id=p1.id, workspace_id=workspace.id, type="Inpatient medicine review", with_provider_name="Dr. Faisal S.", date="05 Oct 2026", time="09:15 AM", status="upcoming", scheduled_by_id=clinician_user.id),
        Appointment(patient_id=p1.id, workspace_id=workspace.id, type="Follow-up · Internal Medicine", with_provider_name="Dr. Faisal S.", date="02 Oct 2026", time="10:30 AM", status="upcoming", scheduled_by_id=clinician_user.id),
        Appointment(patient_id=p1.id, workspace_id=workspace.id, type="Initial consult", with_provider_name="Dr. Faisal S.", date="25 Sep 2026", time="09:00 AM", status="completed", scheduled_by_id=clinician_user.id),
        Appointment(patient_id=p2.id, workspace_id=workspace.id, type="Post-discharge review · Cardiology", with_provider_name="Dr. N. Fatima", date="10 Oct 2026", time="02:00 PM", status="upcoming", scheduled_by_id=admin_user.id),
        Appointment(patient_id=p2.id, workspace_id=workspace.id, type="Cardiac rehabilitation assessment", with_provider_name="Dr. N. Fatima", date="14 Oct 2026", time="11:00 AM", status="upcoming", scheduled_by_id=admin_user.id),
        Appointment(patient_id=p2.id, workspace_id=workspace.id, type="Cardiology consult", with_provider_name="Dr. N. Fatima", date="26 Sep 2026", time="11:15 AM", status="completed", scheduled_by_id=admin_user.id),
        Appointment(patient_id=p3.id, workspace_id=workspace.id, type="GI referral follow-up", with_provider_name="Dr. K. Farooq", date="30 Sep 2026", time="04:00 PM", status="upcoming", scheduled_by_id=clinician_user.id),
        Appointment(patient_id=p3.id, workspace_id=workspace.id, type="Upper Endoscopy & Celiac Panel", with_provider_name="Dr. K. Farooq", date="07 Oct 2026", time="10:00 AM", status="upcoming", scheduled_by_id=clinician_user.id),
        Appointment(patient_id=p3.id, workspace_id=workspace.id, type="Discharge consultation", with_provider_name="Dr. Faisal S.", date="23 Sep 2026", time="11:00 AM", status="completed", scheduled_by_id=clinician_user.id),
        Appointment(patient_id=p4.id, workspace_id=workspace.id, type="Critical care follow-up", with_provider_name="Dr. N. Fatima", date="08 Oct 2026", time="08:30 AM", status="upcoming", scheduled_by_id=admin_user.id),
        Appointment(patient_id=p4.id, workspace_id=workspace.id, type="ICU rounds", with_provider_name="Dr. N. Fatima", date="27 Sep 2026", time="08:00 AM", status="completed", scheduled_by_id=admin_user.id),
    ]
    db.add_all(appts)

    # 11. Documents & Extracted Fields
    d1 = Document(id="d1", patient_id=p1.id, workspace_id=workspace.id, name="intake-form-amina-yusuf.pdf", type="intake_form", status="needs_review", uploaded_by_id=clinician_user.id, source_file_url="files/intake-form-amina-yusuf.pdf")
    d2 = Document(id="d2", patient_id=p1.id, workspace_id=workspace.id, name="lab-report-cbc-25sep.pdf", type="lab_report", status="processed", uploaded_by_id=clinician_user.id, source_file_url="files/lab-report-cbc-25sep.pdf")
    d3 = Document(id="d3", patient_id=p2.id, workspace_id=workspace.id, name="cardiology-consult-note.pdf", type="clinical_note", status="processed", uploaded_by_id=admin_user.id, source_file_url="files/cardiology-consult-note.pdf")
    d4 = Document(id="d4", patient_id=p4.id, workspace_id=workspace.id, name="icu-progress-note-27sep.pdf", type="clinical_note", status="needs_review", uploaded_by_id=admin_user.id, source_file_url="files/icu-progress-note-27sep.pdf")
    d5 = Document(id="d5", patient_id=p3.id, workspace_id=workspace.id, name="discharge-summary-layla-ahmed.pdf", type="discharge_summary", status="processed", uploaded_by_id=clinician_user.id, source_file_url="files/discharge-summary-layla-ahmed.pdf")
    d6 = Document(id="d6", patient_id=p3.id, workspace_id=workspace.id, name="referral-letter-layla-ahmed.pdf", type="referral_letter", status="processed", uploaded_by_id=clinician_user.id, source_file_url="files/referral-letter-layla-ahmed.pdf")
    d7 = Document(id="d7", patient_id=p2.id, workspace_id=workspace.id, name="insurance-claim-hassan-raza.pdf", type="insurance_claim", status="processing", uploaded_by_id=admin_user.id, source_file_url=None)

    db.add_all([d1, d2, d3, d4, d5, d6, d7])
    db.flush()

    extracted_fields = [
        ExtractedField(document_id=d1.id, label="Patient name", value="Amina Yusuf", confidence=0.98, flagged=False),
        ExtractedField(document_id=d1.id, label="Date of birth", value="14 Mar 1988", confidence=0.95, flagged=False),
        ExtractedField(document_id=d1.id, label="Reason for visit", value="Persistent abdominal pain, 3 days", confidence=0.81, flagged=False),
        ExtractedField(document_id=d1.id, label="Known allergies", value="Penicillin (rash/facial swelling from amoxicillin)", confidence=0.92, flagged=True),
        ExtractedField(document_id=d1.id, label="Emergency contact", value="Zainab Yusuf — 0300-7654321", confidence=0.95, flagged=False),
        ExtractedField(document_id=d2.id, label="WBC count", value="13.4 x10⁹/L", confidence=0.97, flagged=True),
        ExtractedField(document_id=d2.id, label="Hemoglobin", value="11.2 g/dL", confidence=0.96, flagged=False),
        ExtractedField(document_id=d2.id, label="Platelets", value="260 x10⁹/L", confidence=0.95, flagged=False),
        ExtractedField(document_id=d2.id, label="CRP", value="38 mg/L", confidence=0.88, flagged=True),
        ExtractedField(document_id=d3.id, label="Diagnosis", value="Stable angina, NYHA class II", confidence=0.89, flagged=False),
        ExtractedField(document_id=d3.id, label="Suggested ICD-10", value="I20.8", confidence=0.74, flagged=True),
        ExtractedField(document_id=d3.id, label="Follow-up", value="Outpatient review in 2 weeks", confidence=0.93, flagged=False),
        ExtractedField(document_id=d4.id, label="Vitals summary", value="BP 128/82, HR 91, SpO2 96%", confidence=0.94, flagged=False),
        ExtractedField(document_id=d4.id, label="Assessment", value="Post-op day 2, stable, monitor for infection", confidence=0.70, flagged=True),
        ExtractedField(document_id=d5.id, label="Primary diagnosis", value="Functional dyspepsia (acute epigastric pain resolved)", confidence=0.94, flagged=False),
        ExtractedField(document_id=d5.id, label="Discharge medication", value="Omeprazole 20mg once daily", confidence=0.96, flagged=False),
        ExtractedField(document_id=d5.id, label="Documented allergies", value="Sulfa drugs, Latex", confidence=0.98, flagged=True),
        ExtractedField(document_id=d5.id, label="Follow-up", value="Gastroenterology with Dr. K. Farooq", confidence=0.91, flagged=False),
        ExtractedField(document_id=d6.id, label="Referred to", value="Dr. K. Farooq, Gastroenterology", confidence=0.97, flagged=False),
        ExtractedField(document_id=d6.id, label="Reason for referral", value="Recurrent epigastric discomfort, rule out structural GI pathology", confidence=0.92, flagged=False),
        ExtractedField(document_id=d6.id, label="Family history", value="Maternal aunt with celiac disease", confidence=0.88, flagged=True),
    ]
    db.add_all(extracted_fields)

    # 12. Discharge Drafts
    draft_p2 = DischargeDraft(patient_id=p2.id, workspace_id=workspace.id, status="draft")
    draft_p3 = DischargeDraft(patient_id=p3.id, workspace_id=workspace.id, status="signed", signed_by_id=clinician_user.id, signed_at=now - timedelta(days=1))
    db.add_all([draft_p2, draft_p3])
    db.flush()

    paras = [
        DischargeParagraph(discharge_draft_id=draft_p2.id, text="Mr. Hassan Raza was admitted for evaluation of exertional chest pain, subsequently diagnosed as stable angina (NYHA class II).", source_citation="cardiology-consult-note.pdf · Page 1", order_index=0),
        DischargeParagraph(discharge_draft_id=draft_p2.id, text="During admission, the patient was started on atorvastatin 40mg nightly and aspirin 75mg daily; metoprolol dosing was flagged for prescriber review prior to discharge.", source_citation="medication-order-26sep.pdf · Page 1", order_index=1),
        DischargeParagraph(discharge_draft_id=draft_p2.id, text="The patient remained hemodynamically stable throughout the admission with no further chest pain episodes reported.", source_citation="nursing-notes-26sep.pdf · Page 3", order_index=2),
        DischargeParagraph(discharge_draft_id=draft_p2.id, text="Patient is discharged in stable condition with outpatient cardiology follow-up scheduled in 2 weeks.", source_citation="cardiology-consult-note.pdf · Page 2", order_index=3),
        DischargeParagraph(discharge_draft_id=draft_p3.id, text="Ms. Layla Ahmed was admitted with acute epigastric pain, diagnosed as functional dyspepsia with symptom resolution on PPI therapy.", source_citation="discharge-summary-layla-ahmed.pdf · Page 1", order_index=0),
        DischargeParagraph(discharge_draft_id=draft_p3.id, text="Discharged on Omeprazole 20mg once daily for 4 weeks. Known allergies to Sulfa drugs and Latex were verified and noted.", source_citation="discharge-summary-layla-ahmed.pdf · Page 1", order_index=1),
        DischargeParagraph(discharge_draft_id=draft_p3.id, text="Formal referral sent to Dr. K. Farooq (Gastroenterology) for outpatient follow-up and evaluation of family celiac history.", source_citation="referral-letter-layla-ahmed.pdf · Page 1", order_index=2),
    ]
    db.add_all(paras)

    # 13. Audit Events
    audits = [
        AuditEvent(workspace_id=workspace.id, actor_user_id=clinician_user.id, patient_id=p1.id, action="patient.viewed", detail="Viewed patient chart"),
        AuditEvent(workspace_id=workspace.id, actor_user_id=admin_user.id, patient_id=p1.id, action="document.extracted", detail="Extracted 5 fields from intake-form-amina-yusuf.pdf"),
        AuditEvent(workspace_id=workspace.id, actor_user_id=clinician_user.id, patient_id=p2.id, action="discharge.draft_reviewed", detail="Reviewed discharge summary draft"),
        AuditEvent(workspace_id=workspace.id, actor_user_id=clinician_user.id, patient_id=p3.id, action="discharge.signed", detail="Signed discharge summary and finalized episode"),
    ]
    db.add_all(audits)

    db.commit()
    print("[✓] Successfully seeded complete demo clinical database: 4 patients, 7 documents, 21 extracted fields, 11 appointments, medications, labs, vitals, immunizations, and discharge drafts.")
