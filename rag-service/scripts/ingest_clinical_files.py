#!/usr/bin/env python3
"""
Clinical Files Ingestion & RAG Training Script for CuraMind RAG Service.
Extracts text and metadata from PDF clinical files in 'files/',
generates semantic vector embeddings, and indexes them into PostgreSQL pgvector + full-text search.
"""
import argparse
import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, List

# Ensure rag-service root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
RAG_ROOT = SCRIPT_DIR.parent
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))

from app.config import settings
from app.db import postgres as db
from app.services.embeddings import get_embedding_provider
from app.services.ingestion import extract_text_from_raw, chunk_text


# File to Patient and Document Metadata Mapping
CLINICAL_FILES_METADATA = {
    "intake-form-amina-yusuf.pdf": {
        "patient_id": "p1",
        "doc_id": "d1",
        "name": "intake-form-amina-yusuf.pdf",
        "type": "Intake form",
        "date": "25 Sep 2026",
        "fields": [
            {"label": "Patient name", "value": "Amina Yusuf", "confidence": 0.98, "flagged": False},
            {"label": "Date of birth", "value": "14 Mar 1988", "confidence": 0.95, "flagged": False},
            {"label": "Reason for visit", "value": "Persistent abdominal pain, 3 days", "confidence": 0.81, "flagged": False},
            {"label": "Known allergies", "value": "Penicillin (rash/facial swelling from amoxicillin)", "confidence": 0.92, "flagged": True},
            {"label": "Emergency contact", "value": "Zainab Yusuf — 0300-7654321", "confidence": 0.95, "flagged": False},
        ]
    },
    "lab-report-cbc-25sep.pdf": {
        "patient_id": "p1",
        "doc_id": "d2",
        "name": "lab-report-cbc-25sep.pdf",
        "type": "Lab report",
        "date": "25 Sep 2026",
        "fields": [
            {"label": "WBC count", "value": "13.4 x10⁹/L", "confidence": 0.97, "flagged": True},
            {"label": "Hemoglobin", "value": "11.2 g/dL", "confidence": 0.96, "flagged": False},
            {"label": "Platelets", "value": "260 x10⁹/L", "confidence": 0.95, "flagged": False},
            {"label": "CRP", "value": "38 mg/L", "confidence": 0.88, "flagged": True},
        ]
    },
    "cardiology-consult-note.pdf": {
        "patient_id": "p2",
        "doc_id": "d3",
        "name": "cardiology-consult-note.pdf",
        "type": "Clinical note",
        "date": "26 Sep 2026",
        "fields": [
            {"label": "Diagnosis", "value": "Stable angina, NYHA class II", "confidence": 0.89, "flagged": False},
            {"label": "Suggested ICD-10", "value": "I20.8", "confidence": 0.74, "flagged": True},
            {"label": "Follow-up", "value": "Outpatient review in 2 weeks", "confidence": 0.93, "flagged": False},
        ]
    },
    "discharge-summary-layla-ahmed.pdf": {
        "patient_id": "p3",
        "doc_id": "d5",
        "name": "discharge-summary-layla-ahmed.pdf",
        "type": "Discharge summary",
        "date": "23 Sep 2026",
        "fields": [
            {"label": "Primary diagnosis", "value": "Functional dyspepsia (acute epigastric pain resolved)", "confidence": 0.94, "flagged": False},
            {"label": "Discharge medication", "value": "Omeprazole 20mg once daily", "confidence": 0.96, "flagged": False},
            {"label": "Documented allergies", "value": "Sulfa drugs, Latex", "confidence": 0.98, "flagged": True},
            {"label": "Follow-up", "value": "Gastroenterology with Dr. K. Farooq", "confidence": 0.91, "flagged": False},
        ]
    },
    "referral-letter-layla-ahmed.pdf": {
        "patient_id": "p3",
        "doc_id": "d6",
        "name": "referral-letter-layla-ahmed.pdf",
        "type": "Referral letter",
        "date": "24 Sep 2026",
        "fields": [
            {"label": "Referred to", "value": "Dr. K. Farooq, Gastroenterology", "confidence": 0.97, "flagged": False},
            {"label": "Reason for referral", "value": "Recurrent epigastric discomfort, rule out structural GI pathology", "confidence": 0.92, "flagged": False},
            {"label": "Family history", "value": "Maternal aunt with celiac disease", "confidence": 0.88, "flagged": True},
        ]
    }
}


async def ingest_files(files_dir: Path, workspace_id: str, user_id: str = "system-seeder") -> Dict[str, Any]:
    """
    Ingests all PDF files in `files_dir` into the active RAG store (PostgreSQL or fallback store).
    """
    if not files_dir.exists():
        raise FileNotFoundError(f"Files directory not found: {files_dir}")

    embedding_provider = get_embedding_provider()
    print(f"[*] Starting ingestion for workspace '{workspace_id}' using embedding provider: {embedding_provider.__class__.__name__}")
    
    total_docs = 0
    total_chunks = 0
    total_fields = 0

    pdf_files = list(files_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"[!] No PDF files found in {files_dir}")
        return {"total_docs": 0, "total_chunks": 0}

    for pdf_path in pdf_files:
        filename = pdf_path.name
        meta = CLINICAL_FILES_METADATA.get(filename, {
            "patient_id": "p1",
            "doc_id": str(uuid.uuid4()),
            "name": filename,
            "type": "Clinical note",
            "date": "25 Sep 2026",
            "fields": []
        })

        file_bytes = pdf_path.read_bytes()
        full_text, pages_data = extract_text_from_raw(file_bytes, filename)
        
        print(f" -> Processing '{filename}' (Patient: {meta['patient_id']}, {len(file_bytes)} bytes, {len(pages_data)} pages)")

        # 1. Insert or update document record
        doc_record = {
            "id": meta["doc_id"],
            "workspace_id": workspace_id,
            "patient_id": meta["patient_id"],
            "name": meta["name"],
            "type": meta["type"],
            "date": meta["date"],
            "status": "processing",
            "full_text": full_text,
            "source": f"files/{filename}",
        }
        await db.insert_document(doc_record)

        # 2. Insert Extracted Fields
        for field in meta.get("fields", []):
            await db.insert_extracted_field({
                "id": str(uuid.uuid4()),
                "document_id": meta["doc_id"],
                "workspace_id": workspace_id,
                "label": field["label"],
                "value": field["value"],
                "confidence": field.get("confidence", 0.9),
                "flagged": field.get("flagged", False),
            })
            total_fields += 1

        # 3. Create chunks and generate embeddings
        raw_chunks = chunk_text(pages_data, chunk_size=500, chunk_overlap=50)
        if not raw_chunks:
            raw_chunks = [{"chunk_text": full_text[:500], "page_number": 1, "chunk_index": 0}]

        chunk_texts = [c["chunk_text"] for c in raw_chunks]
        embeddings = embedding_provider.embed_batch(chunk_texts)

        chunk_records = []
        for idx, (c, emb) in enumerate(zip(raw_chunks, embeddings)):
            chunk_records.append({
                "id": str(uuid.uuid4()),
                "document_id": meta["doc_id"],
                "workspace_id": workspace_id,
                "patient_id": meta["patient_id"],
                "chunk_text": c["chunk_text"],
                "page_number": c["page_number"],
                "chunk_index": idx,
                "embedding": emb,
            })

        await db.insert_chunks(chunk_records)
        await db.update_document(meta["doc_id"], {"status": "processed"})
        await db.log_audit({
            "workspace_id": workspace_id,
            "user_id": user_id,
            "user_email": "system@curamind.local",
            "patient_id": meta["patient_id"],
            "action": "document.ingested_cli",
            "detail": f"Ingested '{filename}' with {len(chunk_records)} chunks and {len(meta.get('fields', []))} fields."
        })

        total_docs += 1
        total_chunks += len(chunk_records)
        print(f"    [+] Successfully indexed '{filename}' into {len(chunk_records)} vector chunks.")

    print(f"\n[✓] Clinical files ingestion complete: {total_docs} documents, {total_chunks} chunks, {total_fields} extracted fields.")
    return {
        "total_docs": total_docs,
        "total_chunks": total_chunks,
        "total_fields": total_fields
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest clinical PDF files into CuraMind RAG vector index")
    parser.add_argument("--files-dir", default=str(RAG_ROOT.parent / "files"), help="Path to clinical files directory")
    parser.add_argument("--workspace-id", default="default-workspace", help="Target Workspace ID")
    parser.add_argument("--user-id", default="admin-user-id", help="User ID for audit logs")
    args = parser.parse_args()

    files_path = Path(args.files_dir).resolve()
    asyncio.run(ingest_files(files_path, args.workspace_id, args.user_id))


if __name__ == "__main__":
    main()
