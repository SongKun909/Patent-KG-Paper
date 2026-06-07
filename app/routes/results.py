"""Results routes: query quintuples, export CSV."""
import csv
import io
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.quintuple import Quintuple
from app.templating import templates

router = APIRouter(prefix="/api/results", tags=["results"])


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


@router.get("/")
def list_results(
    request: Request,
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
    result_items = [
        {
            "id": r.id,
            "patent_id": r.patent_id,
            "name": r.name,
            "value": r.value,
            "relation": r.relation,
            "object": r.object,
            "condition": r.condition,
            "confidence": r.confidence,
        }
        for r in items
    ]
    if _is_htmx(request):
        return templates.TemplateResponse(
            "partials/result_rows.html",
            {"request": request, "items": result_items, "total": total, "page": page},
        )
    return {"items": result_items, "total": total, "page": page}


@router.get("/export")
def export_results(
    patent_id: int = None,
    db: Session = Depends(get_db),
):
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
                "id": r.id, "name": r.name, "value": r.value,
                "relation": r.relation, "object": r.object,
                "condition": r.condition, "source_text": r.source_text,
                "confidence": r.confidence,
            }
            for r in items
        ],
    }
