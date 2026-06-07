"""Results routes: query quintuples, export CSV."""
import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.quintuple import Quintuple

router = APIRouter(prefix="/api/results", tags=["results"])


@router.get("/")
def list_results(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    patent_id: int = None,
    name: str = None,
    db: Session = Depends(get_db),
):
    q = db.query(Quintuple)
    if patent_id:
        q = q.filter(Quintuple.patent_id == patent_id)
    if name:
        q = q.filter(Quintuple.name.ilike(f"%{name}%"))
    total = q.count()
    items = (
        q.order_by(desc(Quintuple.extracted_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "patent_id": r.patent_id,
                "name": r.name,
                "value": r.value,
                "relation": r.relation,
                "object": r.object,
                "condition": r.condition,
                "source_text": r.source_text[:200] if r.source_text else "",
                "confidence": r.confidence,
                "extracted_at": r.extracted_at.isoformat() if r.extracted_at else None,
            }
            for r in items
        ],
        "total": total,
        "page": page,
    }


@router.get("/export")
def export_results(
    patent_id: int = None,
    db: Session = Depends(get_db),
):
    """Export quintuples as CSV."""
    q = db.query(Quintuple)
    if patent_id:
        q = q.filter(Quintuple.patent_id == patent_id)
    items = q.order_by(Quintuple.extracted_at).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "PatentID", "Name", "Value", "Relation", "Object", "Condition", "Confidence"])
    for r in items:
        writer.writerow([r.id, r.patent_id, r.name, r.value, r.relation, r.object, r.condition, f"{r.confidence:.2f}"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=quintuples_export.csv"},
    )


@router.get("/patent/{patent_id}")
def get_patent_results(patent_id: int, db: Session = Depends(get_db)):
    """Get all quintuples for a specific patent."""
    items = (
        db.query(Quintuple)
        .filter(Quintuple.patent_id == patent_id)
        .order_by(Quintuple.extracted_at)
        .all()
    )
    return {
        "patent_id": patent_id,
        "count": len(items),
        "quintuples": [
            {
                "id": r.id,
                "name": r.name,
                "value": r.value,
                "relation": r.relation,
                "object": r.object,
                "condition": r.condition,
                "source_text": r.source_text,
                "confidence": r.confidence,
            }
            for r in items
        ],
    }
