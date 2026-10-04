import difflib
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from app.db import postgres as db
from app.schemas.comparison import (
    DocumentComparisonResponse,
    StructuredFieldDiff,
    TextDiffSection,
)

logger = logging.getLogger("rag_service.comparison")


async def compare_documents(
    doc1_id: str,
    doc2_id: str,
    workspace_id: str,
    mode: str = "both"
) -> DocumentComparisonResponse:
    """
    Deterministic document comparison service.
    
    Guarantees:
    1. Rejects any cross-workspace document access.
    2. Compares structured extracted fields (chief complaint, diagnosis, vitals, etc.).
    3. Compares full-text lines with difflib sequence matching.
    """
    doc1 = await db.get_document(doc1_id, workspace_id=workspace_id)
    doc2 = await db.get_document(doc2_id, workspace_id=workspace_id)

    if not doc1 or not doc2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both documents not found in the current workspace"
        )

    # 1. Structured Field Comparison
    fields1 = await db.list_extracted_fields(doc1_id, workspace_id=workspace_id)
    fields2 = await db.list_extracted_fields(doc2_id, workspace_id=workspace_id)

    dict1 = {f["label"]: f["value"] for f in fields1}
    dict2 = {f["label"]: f["value"] for f in fields2}

    all_labels = sorted(set(list(dict1.keys()) + list(dict2.keys())))
    structured_diffs: List[StructuredFieldDiff] = []
    diff_count = 0

    for label in all_labels:
        v1 = dict1.get(label)
        v2 = dict2.get(label)

        if v1 is not None and v2 is not None:
            if v1.strip().lower() == v2.strip().lower():
                structured_diffs.append(StructuredFieldDiff(
                    label=label,
                    doc1_value=v1,
                    doc2_value=v2,
                    status="matched"
                ))
            else:
                diff_count += 1
                structured_diffs.append(StructuredFieldDiff(
                    label=label,
                    doc1_value=v1,
                    doc2_value=v2,
                    status="differ"
                ))
        elif v1 is not None:
            diff_count += 1
            structured_diffs.append(StructuredFieldDiff(
                label=label,
                doc1_value=v1,
                doc2_value=None,
                status="only_in_doc1"
            ))
        else:
            diff_count += 1
            structured_diffs.append(StructuredFieldDiff(
                label=label,
                doc1_value=None,
                doc2_value=v2,
                status="only_in_doc2"
            ))

    # 2. Full-Text Sequence Comparison
    text_diffs: List[TextDiffSection] = []
    lines1 = (doc1.get("full_text") or "").splitlines()
    lines2 = (doc2.get("full_text") or "").splitlines()

    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        diff_count += 1
        text_diffs.append(TextDiffSection(
            tag=tag,
            doc1_lines=lines1[i1:i2],
            doc2_lines=lines2[j1:j2],
            doc1_page=None,
            doc2_page=None,
        ))

    summary_text = (
        f"Compared '{doc1['name']}' against '{doc2['name']}'. "
        f"Found {diff_count} total differences across structured fields and text passages."
        if diff_count > 0 else
        f"Documents '{doc1['name']}' and '{doc2['name']}' are identical across compared sections."
    )

    return DocumentComparisonResponse(
        doc1_id=doc1_id,
        doc1_name=doc1["name"],
        doc2_id=doc2_id,
        doc2_name=doc2["name"],
        workspace_id=workspace_id,
        patient_id=doc1["patient_id"],
        structured_diffs=structured_diffs,
        text_diffs=text_diffs,
        summary=summary_text,
        total_differences_count=diff_count,
    )
