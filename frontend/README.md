# CuraMind

AI Document Intelligence & RAG platform — frontend.

A React + Vite single-page app with a sidebar-driven workspace: Dashboard, Documents,
Upload, Ask AI (RAG chat with citations), Compare, and Settings. Currently wired to
mock data in `src/data/mock.js` — swap that out for real API calls to your FastAPI
backend when it's ready.

## Folder structure

```
documind-app/
├── index.html                 # Vite entry HTML
├── package.json
├── vite.config.js
├── README.md
└── src/
    ├── main.jsx                # React root
    ├── App.jsx                 # Top-level layout + view routing (incl. patient drill-down)
    ├── styles/
    │   └── index.css           # Design tokens + all component styles
    ├── components/
    │   ├── icons.jsx            # Shared inline SVG icon set
    │   ├── Sidebar.jsx          # Left nav, CuraMind wordmark, user chip
    │   ├── Topbar.jsx           # Page title, search, upload button
    │   ├── Badge.jsx            # Status pill (processed/processing/failed)
    │   └── Confidence.jsx       # AI extraction confidence pill (high/mid/low)
    ├── pages/
    │   ├── Dashboard.jsx        # Stats, documents-by-type, activity feed
    │   ├── Documents.jsx        # Filterable document table
    │   ├── Upload.jsx           # Dropzone + processing pipeline tracker
    │   ├── Ask.jsx               # RAG chat with source citations
    │   ├── Compare.jsx           # Side-by-side document comparison
    │   ├── Settings.jsx          # Workspace preference toggles
    │   ├── Patients.jsx          # Healthcare: patient roster, ward/status filters
    │   ├── PatientDetail.jsx     # Healthcare: patient chart shell, tabs, PHI toggle
    │   └── patient/
    │       ├── DocumentReview.jsx    # Confidence-scored fields, human-in-the-loop confirm
    │       ├── LabTrends.jsx         # Inline SVG lab value trend charts + reference ranges
    │       ├── Medications.jsx       # Medication reconciliation, allergy/dosage flags
    │       ├── DischargeSummary.jsx  # AI-drafted discharge summary with citations + sign-off
    │       └── AuditLog.jsx          # Per-patient audit trail
    └── data/
        ├── mock.js               # Document-workspace placeholder data
        └── patientMock.js        # Healthcare placeholder data (patients, labs, meds, audit)
```

### Healthcare module

A new **Patients** section in the sidebar leads to a roster (filterable by admission status)
and, per patient, a chart workspace with five tabs:

- **Documents** — extracted fields shown with a confidence score and a human "Confirm" step;
  low-confidence or clinically sensitive fields (e.g. allergies) are flagged for review rather
  than auto-accepted.
- **Lab trends** — values plotted over time against a reference range, with out-of-range points
  called out.
- **Medications** — reconciliation list with allergy-conflict and dosage flags a pharmacist or
  clinician must clear.
- **Discharge summary** — an AI-drafted summary where every sentence carries a citation back to
  its source document; it only becomes part of the record after a clinician clicks
  "Approve & sign."
- **Audit log** — who viewed or changed what, and when.

The patient header also has a **Show/Hide PHI** toggle that masks the patient's name and date of
birth in the UI — a stand-in for real field-level redaction, which in production should be backed
by actual access-control and encryption on the API/data layer, not just a client-side toggle.

### Patient chart now matches what real hospital EHR/patient-portal systems track

Based on a look at how production EHR systems (Oracle Health, Epic MyChart and similar) and the
IOM's core EHR capability guidance structure a patient record, the chart now has seven tabs instead
of five:

- **Overview** *(new)* — demographics, contact and emergency contact info, blood type, insurance
  provider and policy number, assigned attending physician/ward, latest vitals snapshot, and
  immunization history. This is the "administrative + clinical summary" data every EHR treats as
  the core record, and it's what `AddPatientForm` now captures on intake.
- **Documents** — confidence-scored extraction with human review (unchanged).
- **Lab trends** — unchanged.
- **Medications** — unchanged.
- **Appointments** *(new)* — upcoming/past visit history plus a "Schedule appointment" form,
  matching the scheduling feature every hospital patient portal leads with.
- **Discharge summary** — unchanged.
- **Audit log** — unchanged.

### Live state, not just static mock data

The app is now seeded from `src/data/patientMock.js` but runs on a real state layer
(`src/context/PatientContext.jsx`, a React Context + `useState`, persisted to `localStorage`
so it survives a page refresh — this is a real npm project, not a published preview, so
browser storage is the right tool here). This means:

- **Add patient** (Patients page) opens a form (name, DOB, sex, ward, allergies, admission
  reason) and creates a real chart — it appears in the roster and can be opened immediately.
- **Add document** (inside a patient chart, or from the global Upload page with a patient
  selector) runs a simulated extraction pipeline and adds a document with confidence-scored
  fields to that patient's chart — it does not parse a real file yet, but the shape of the data
  it produces matches what a real OCR/LLM extraction step would return.
- **Confirm field** permanently clears a flag and writes an audit entry.
- **Approve & sign** on a discharge summary updates the patient's status and writes an audit
  entry.
- The **Dashboard** now shows live counts (patients admitted, documents indexed, fields
  needing review) computed from this shared state, not hardcoded numbers.

Every document type in the facility-wide **Document Vault** and every message in the
**Clinical Assistant** demo is now clinical (lab reports, clinical notes, referrals, discharge
summaries, insurance claims) rather than the original invoices/contracts placeholder content.

Nothing here auto-finalizes a clinical decision, a diagnosis, or a record — every AI-suggested
value requires an explicit human confirmation, by design. To wire this to a real backend, replace
the body of each function in `PatientContext.jsx` (`addPatient`, `addDocument`, `confirmField`,
`signDischarge`) with a `fetch`/React Query call to your FastAPI endpoints, keeping the same
function signatures so no page component needs to change.

## Getting started

```bash
npm install
npm run dev
```

Then open http://localhost:5173.

## Build for production

```bash
npm run build
npm run preview
```

## Wiring up the real backend

Replace the contents of `src/data/mock.js` with data fetched from your FastAPI
endpoints (e.g. `GET /documents`, `POST /documents/upload`, `POST /ask`), and swap
the `useState` initial values in `pages/Ask.jsx`, `pages/Documents.jsx`, and
`pages/Upload.jsx` for real fetch/mutation calls (React Query or plain `fetch` in a
`useEffect` both work fine here). The pipeline steps in `Upload.jsx` map directly to
the ingestion pipeline stages described in the project spec (upload → extract → OCR →
clean → classify → extract fields → validate → embed → index).
