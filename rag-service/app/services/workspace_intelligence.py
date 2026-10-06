"""
CuraMind Workspace Intelligence Layer.

Handles queries about the application's own data (patient counts, appointments,
discharged patients, documents, etc.) by fetching live data from the backend API.
This layer intercepts BEFORE the RAG document retriever so the user gets answers
even when no clinical PDF has been indexed.

Intent detection uses a synonym-aware keyword map so that queries like:
  - "how many records"  → patient/record count
  - "who is admitted"   → admission status
  - "any appointments"  → appointment list
  - "show me discharged patients" → discharge info
all resolve correctly without an LLM.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("rag_service.workspace_intelligence")

# ---------------------------------------------------------------------------
# Backend base URL (core backend is always on port 8000)
# ---------------------------------------------------------------------------
BACKEND_BASE = "http://localhost:8000/api/v1"


# ---------------------------------------------------------------------------
# Intent taxonomy — maps query intent → (label, backend_endpoint, description)
# ---------------------------------------------------------------------------

# Synonym clusters — any token in a group is equivalent
SYNONYM_CLUSTERS = [
    # Patient / record
    {"patient", "patients", "record", "records", "person", "persons", "people",
     "individual", "individuals", "case", "cases", "client", "clients"},
    # Count / number
    {"how", "many", "count", "number", "total", "much", "much", "quantity",
     "how many", "how much", "how much", "few", "any"},
    # Admitted / active
    {"admitted", "admit", "admission", "inpatient", "inpatients", "active",
     "current", "ward", "hospitalized", "hospitalised", "bed"},
    # Discharged
    {"discharged", "discharge", "discharges", "left", "released", "sent home",
     "checkout", "checked out", "went home"},
    # Appointment
    {"appointment", "appointments", "visit", "visits", "schedule", "scheduled",
     "booking", "bookings", "consult", "consultation", "consultations",
     "upcoming", "next visit", "follow-up", "followup"},
    # Documents / vault
    {"document", "documents", "doc", "docs", "file", "files", "report",
     "reports", "vault", "uploaded", "indexed", "pdf", "pdfs", "chart",
     "charts", "record", "records"},
    # Lab / test
    {"lab", "labs", "laboratory", "test", "tests", "result", "results",
     "bloodwork", "blood test", "pathology", "panel", "panels"},
    # Medication
    {"medication", "medications", "medicine", "medicines", "drug", "drugs",
     "prescription", "prescriptions", "med", "meds", "rx"},
    # Staff / team
    {"doctor", "doctors", "physician", "physicians", "clinician", "clinicians",
     "nurse", "nurses", "staff", "team", "attending"},
]

def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


def _tokens(text: str) -> List[str]:
    return _normalize(text).split()


def _has_any(tokens: List[str], *words: str) -> bool:
    """Return True if any of the given words appear in the token list."""
    return any(w in tokens for w in words)


def _contains_phrase(text: str, *phrases: str) -> bool:
    """Return True if any phrase is a substring of normalized text."""
    n = _normalize(text)
    return any(p in n for p in phrases)


# ---------------------------------------------------------------------------
# Intent classifiers — pure Python, no network
# ---------------------------------------------------------------------------

def _is_clinical_document_query(q: str) -> bool:
    """
    Returns True if the query is clearly asking about clinical data IN a document
    (measurements, values, medications, symptoms, procedures) rather than app-level data.
    These queries must NOT be intercepted by the workspace intelligence layer.
    """
    clinical_signals = (
        # Vital signs / measurements
        "blood pressure", "bp", "heart rate", "pulse", "temperature", "spo2",
        "oxygen saturation", "weight", "bmi", "height", "respiratory rate",
        # Lab values / test results
        "hba1c", "glucose", "cholesterol", "lipid", "hemoglobin", "wbc", "rbc",
        "platelet", "creatinine", "egfr", "sodium", "potassium", "magnesium",
        "calcium", "albumin", "bilirubin", "alt", "ast", "tsh", "troponin",
        "inr", "pt", "aptt", "d-dimer", "ferritin", "psa", "cbc",
        # Clinical query patterns — questions about VALUES in documents
        "what was", "what is the", "what are the", "what medication",
        "what drug", "what dose", "what dosage", "what diagnosis",
        "what condition", "what treatment", "what procedure", "what finding",
        "is the patient allergic", "patient allergic", "patient's allergy",
        "patient's medication", "patient's diagnosis", "patient's condition",
        "patient's blood", "patient's lab", "patient's vital",
        "prescribed", "prescription", "side effect", "contraindication",
        "mg", "mcg", "ml", "mmhg", "mmol", "iu/l", "g/dl", "ng/ml",
        "symptom", "complaint", "presenting with", "chief complaint",
        "history of", "past medical", "family history",
        "surgery", "operation", "procedure",
        "finding", "impression", "assessment",
        "allerg", "hypersensit", "intoleran",
        "admission blood", "admission bp", "admission pressure",
        "admission glucose", "admission vitals",
        "discharge summary", "follow-up action",
    )
    return any(sig in q for sig in clinical_signals)


def detect_app_intent(query: str) -> Optional[str]:
    """
    Classify query into an app-level intent category.

    IMPORTANT: Clinical document questions (blood pressure values, medication names,
    lab results, symptoms etc.) are NEVER intercepted here — they go to the RAG retriever.

    Returns one of:
      "patient_count"    — How many patients / records are there?
      "admitted_list"    — Who is currently admitted?
      "discharged_list"  — Who has been discharged?
      "appointment_list" — What appointments are upcoming?
      "document_count"   — How many documents/files in the vault?
      "dashboard_stats"  — General dashboard / system overview
      "patient_detail"   — Tell me about a specific patient (by name/MRN)
      None               — Not an app-level query (routes to RAG retriever)
    """
    q = _normalize(query)
    tokens = q.split()

    # ── Guard: Never intercept clinical document questions ────────────────────
    if _is_clinical_document_query(q):
        return None

    is_count = _has_any(tokens, "how", "many", "count", "total", "number")
    is_list  = _has_any(tokens, "list", "show", "who", "which", "give", "all")

    # Dashboard / overview / statistics
    if _contains_phrase(q, "dashboard", "overview", "statistics", "stats",
                         "summary of app", "summary of system", "system summary",
                         "what data do you have", "what information do you have",
                         "what is in the app", "what is in the system",
                         "all data", "entire system", "what can you tell me about the system"):
        return "dashboard_stats"

    # Patient / record count — must be explicit count queries
    if _contains_phrase(q, "how many patient", "how many record", "how many case",
                          "patient count", "record count", "total patient",
                          "number of patient", "number of record",
                          "how many people", "how many person"):
        return "patient_count"

    # Explicit count queries with patient/record nouns
    if is_count and _has_any(tokens, "patient", "patients", "record", "records",
                              "case", "cases", "person", "people"):
        return "patient_count"

    # Admitted patients — only if explicitly asking about the list/count, not a clinical value
    if _contains_phrase(q, "who is admitted", "who is currently admitted",
                          "list admitted", "show admitted", "all admitted",
                          "list inpatients", "show inpatients", "current inpatients",
                          "who is in the ward", "who is in ward",
                          "active patients", "current patients",
                          "how many admitted", "admitted patient"):
        return "admitted_list"

    # Discharged patients — only explicit list/count queries
    if _contains_phrase(q, "who is discharged", "who has been discharged",
                          "list discharged", "show discharged", "all discharged",
                          "how many discharged", "discharge pending",
                          "who was sent home", "who was released",
                          "discharged patient"):
        return "discharged_list"

    # Appointments — explicit appointment queries (not clinical follow-up content)
    if _contains_phrase(q, "how many appointment", "list appointment", "show appointment",
                          "upcoming appointment", "scheduled appointment",
                          "appointment list", "any appointment"):
        return "appointment_list"

    # Documents / vault — explicit vault queries
    if _contains_phrase(q, "how many document", "how many file", "how many pdf",
                          "document vault", "vault document", "list document",
                          "show document", "indexed document", "uploaded document",
                          "number of document", "number of file"):
        return "document_count"

    # Patient detail by MRN
    if re.search(r'\bMRN[-\s]?\d+\b', query, re.IGNORECASE):
        return "patient_detail"

    # Patient detail by explicit name mention (only specific known names)
    if _contains_phrase(q, "tell me about patient", "show patient profile",
                          "patient amina", "patient hassan", "patient layla",
                          "patient omar", "about amina yusuf", "about hassan raza",
                          "about layla ahmed"):
        return "patient_detail"


    return None


# ---------------------------------------------------------------------------
# Backend API data fetcher
# ---------------------------------------------------------------------------

async def _fetch_backend(endpoint: str, token: str) -> Optional[Any]:
    """Fetch JSON data from the backend API. Returns None on failure."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{BACKEND_BASE}{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Backend API fetch failed for {endpoint}: {e}")
    return None


# ---------------------------------------------------------------------------
# Response formatters — convert API payloads to readable assistant text
# ---------------------------------------------------------------------------

def _fmt_patient_count(patients: List[Dict]) -> str:
    if not patients:
        return "There are currently **no patients** registered in the system."

    total = len(patients)
    admitted = [p for p in patients if p.get("status") == "admitted"]
    discharged = [p for p in patients if p.get("status") == "discharged"]
    pending = [p for p in patients if p.get("status") == "discharge-pending"]
    outpatient = [p for p in patients if p.get("status") == "outpatient"]

    lines = [
        f"### 📊 Patient Registry — {total} Patients",
        "",
        f"| Status | Count |",
        f"|--------|-------|",
        f"| 🏥 Admitted (Inpatient) | {len(admitted)} |",
        f"| ✅ Discharged | {len(discharged)} |",
        f"| ⏳ Discharge Pending | {len(pending)} |",
        f"| 🏃 Outpatient | {len(outpatient)} |",
        f"| **Total** | **{total}** |",
        "",
    ]
    if admitted:
        lines.append("**Currently Admitted:**")
        for p in admitted:
            lines.append(f"• {p.get('name', 'Unknown')} — {p.get('ward', 'Ward unknown')} · MRN {p.get('mrn', 'N/A')}")
    return "\n".join(lines)


def _fmt_admitted_list(patients: List[Dict]) -> str:
    admitted = [p for p in patients if p.get("status") == "admitted"]
    pending  = [p for p in patients if p.get("status") == "discharge-pending"]

    if not admitted and not pending:
        return "There are currently **no admitted inpatients** in the system."

    lines = ["### 🏥 Current Inpatients", ""]
    if admitted:
        lines.append(f"**Admitted ({len(admitted)}):**")
        for p in admitted:
            lines.append(
                f"• **{p.get('name')}** · MRN {p.get('mrn', 'N/A')} · "
                f"{p.get('ward', 'Unknown ward')} · "
                f"Attending: {p.get('attending', 'N/A')}"
            )
    if pending:
        lines.append(f"\n**Discharge Pending ({len(pending)}):**")
        for p in pending:
            lines.append(
                f"• **{p.get('name')}** · MRN {p.get('mrn', 'N/A')} · "
                f"{p.get('ward', 'Unknown ward')}"
            )
    return "\n".join(lines)


def _fmt_discharged_list(patients: List[Dict]) -> str:
    discharged = [p for p in patients if p.get("status") in ("discharged", "discharge-pending")]
    if not discharged:
        return "No patients have been discharged recently."

    lines = ["### ✅ Discharged / Pending Discharge", ""]
    for p in discharged:
        status_label = "Discharged" if p.get("status") == "discharged" else "Discharge Pending"
        lines.append(
            f"• **{p.get('name')}** [{status_label}] · MRN {p.get('mrn', 'N/A')} · "
            f"Attending: {p.get('attending', 'N/A')}"
        )
    return "\n".join(lines)


def _fmt_appointments(appointments: List[Dict]) -> str:
    if not appointments:
        return "There are currently **no appointments** scheduled in the system."

    lines = [f"### 📅 Appointments ({len(appointments)} total)", ""]
    for apt in appointments[:10]:  # cap to 10 for readability
        patient = apt.get("patient_name") or apt.get("patient_id", "Unknown Patient")
        date    = apt.get("scheduled_date") or apt.get("date", "TBD")
        purpose = apt.get("purpose") or apt.get("type") or apt.get("reason", "Consultation")
        status  = apt.get("status", "scheduled").title()
        doctor  = apt.get("doctor") or apt.get("attending", "")
        line = f"• **{patient}** — {purpose} · {date}"
        if doctor:
            line += f" · {doctor}"
        line += f" · [{status}]"
        lines.append(line)

    if len(appointments) > 10:
        lines.append(f"\n*... and {len(appointments) - 10} more appointments.*")
    return "\n".join(lines)


def _fmt_document_count(documents: List[Dict]) -> str:
    if not documents:
        return "The document vault is currently **empty** — no documents have been uploaded."

    total = len(documents)
    by_type: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    for doc in documents:
        t = doc.get("type") or doc.get("document_type", "Unknown")
        s = doc.get("status", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        by_status[s] = by_status.get(s, 0) + 1

    lines = [f"### 📂 Document Vault — {total} Documents", ""]
    lines.append("**By Type:**")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append(f"• {t}: {n}")
    lines.append("\n**By Status:**")
    for s, n in sorted(by_status.items(), key=lambda x: -x[1]):
        lines.append(f"• {s.title()}: {n}")

    lines.append("\n**Recent Documents:**")
    for doc in documents[:5]:
        name   = doc.get("name", "Unnamed")
        date   = doc.get("date") or doc.get("created_at", "")
        patient = doc.get("patient_name") or doc.get("patient_id", "")
        entry = f"• **{name}**"
        if patient:
            entry += f" — {patient}"
        if date:
            entry += f" · {str(date)[:10]}"
        lines.append(entry)

    return "\n".join(lines)


def _fmt_dashboard_stats(patients: List[Dict], appointments: List[Dict], documents: List[Dict]) -> str:
    admitted  = sum(1 for p in patients if p.get("status") == "admitted")
    discharged = sum(1 for p in patients if p.get("status") == "discharged")
    pending   = sum(1 for p in patients if p.get("status") == "discharge-pending")
    upcoming_apt = sum(1 for a in appointments if a.get("status") in ("scheduled", "confirmed", "upcoming"))

    lines = [
        "### 🏥 CuraMind Workspace — Live System Overview",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Patients | **{len(patients)}** |",
        f"| Currently Admitted | **{admitted}** |",
        f"| Discharged | **{discharged}** |",
        f"| Discharge Pending | **{pending}** |",
        f"| Total Appointments | **{len(appointments)}** |",
        f"| Upcoming Appointments | **{upcoming_apt}** |",
        f"| Documents in Vault | **{len(documents)}** |",
        "",
    ]

    if patients:
        lines.append("**Registered Patients:**")
        for p in patients:
            status_icon = {"admitted": "🏥", "discharged": "✅", "discharge-pending": "⏳", "outpatient": "🏃"}.get(
                p.get("status", ""), "👤")
            lines.append(
                f"  {status_icon} **{p.get('name')}** · MRN {p.get('mrn')} · "
                f"{p.get('status', 'unknown').replace('-', ' ').title()}"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

async def answer_workspace_query(
    query: str,
    token: str,
    workspace_id: str,
) -> Optional[str]:
    """
    Attempt to answer a workspace-level query using live backend data.

    Returns:
      A formatted string answer if the query is app-level, or
      None if the query should be routed to the RAG document retriever.
    """
    intent = detect_app_intent(query)
    if intent is None:
        return None

    logger.info(f"Workspace intelligence handling query intent='{intent}' for workspace={workspace_id}")

    # Fetch data in parallel where possible
    patients_data     = await _fetch_backend(f"/patients?workspace_id={workspace_id}", token) or []
    appointments_data = await _fetch_backend(f"/appointments?workspace_id={workspace_id}", token) or []
    documents_data    = await _fetch_backend(f"/documents?workspace_id={workspace_id}", token) or []

    # Unwrap paginated or nested responses
    if isinstance(patients_data, dict):
        patients_data = patients_data.get("items") or patients_data.get("patients") or patients_data.get("data") or []
    if isinstance(appointments_data, dict):
        appointments_data = appointments_data.get("items") or appointments_data.get("appointments") or appointments_data.get("data") or []
    if isinstance(documents_data, dict):
        documents_data = documents_data.get("items") or documents_data.get("documents") or documents_data.get("data") or []

    if intent == "patient_count":
        return _fmt_patient_count(patients_data)
    elif intent == "admitted_list":
        return _fmt_admitted_list(patients_data)
    elif intent == "discharged_list":
        return _fmt_discharged_list(patients_data)
    elif intent == "appointment_list":
        return _fmt_appointments(appointments_data)
    elif intent == "document_count":
        return _fmt_document_count(documents_data)
    elif intent == "dashboard_stats":
        return _fmt_dashboard_stats(patients_data, appointments_data, documents_data)
    elif intent == "patient_detail":
        # Extract the patient name from the query for targeted lookup
        q_low = query.lower()
        matched = [p for p in patients_data if p.get("name", "").lower() in q_low or
                   (p.get("mrn", "").lower() in q_low)]
        if matched:
            return _fmt_admitted_list(matched) if matched[0].get("status") == "admitted" else _fmt_patient_count(matched)
        return _fmt_patient_count(patients_data)

    return None
