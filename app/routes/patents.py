"""Patent routes: upload, import, list, delete."""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.patent import Patent
from app.schemas.patent import PatentResponse
from app.config import settings
from app.templating import templates

router = APIRouter(prefix="/api/patents", tags=["patents"])


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


@router.get("/")
def list_patents(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    lang: str = None,
    db: Session = Depends(get_db),
):
    q = db.query(Patent)
    if lang:
        q = q.filter(Patent.lang == lang)
    total = q.count()
    items = (
        q.order_by(desc(Patent.uploaded_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    if _is_htmx(request):
        return templates.TemplateResponse(
            "partials/patent_rows.html",
            {"request": request, "items": items, "total": total, "page": page},
        )
    return {
        "items": [PatentResponse.model_validate(p) for p in items],
        "total": total,
        "page": page,
    }


@router.post("/upload")
async def upload_patent(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")
    upload_dir = Path(settings.PDF_STORAGE_DIR) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    lang = "en" if file.filename.upper().startswith("US") else "zh"
    patent = Patent(
        filename=file.filename,
        file_path=str(file_path),
        lang=lang,
        file_size=os.path.getsize(file_path),
    )
    db.add(patent)
    db.commit()
    db.refresh(patent)
    if _is_htmx(request):
        return HTMLResponse(
            f'<div class="text-sm text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-lg p-3 mt-3">'
            f'上传成功：{patent.filename}（ID: {patent.id}）'
            f'</div>',
            headers={"HX-Trigger": "patentUploaded"},
        )
    return PatentResponse.model_validate(patent)


@router.post("/import", response_model=dict)
def import_from_directory(
    directory: str = Query(...),
    db: Session = Depends(get_db),
):
    if not os.path.isdir(directory):
        raise HTTPException(400, f"Directory not found: {directory}")
    imported = 0
    for fname in sorted(os.listdir(directory)):
        if not fname.lower().endswith(".pdf"):
            continue
        fpath = os.path.join(directory, fname)
        if db.query(Patent).filter(Patent.file_path == fpath).first():
            continue
        lang = "en" if "US" in fname.upper()[:6] else "zh"
        patent = Patent(
            filename=fname, file_path=fpath, lang=lang, file_size=os.path.getsize(fpath)
        )
        db.add(patent)
        imported += 1
    db.commit()
    return {"imported": imported}


@router.delete("/{patent_id}")
def delete_patent(request: Request, patent_id: int, db: Session = Depends(get_db)):
    patent = db.query(Patent).filter(Patent.id == patent_id).first()
    if not patent:
        raise HTTPException(404, "Patent not found")
    db.delete(patent)
    db.commit()
    if _is_htmx(request):
        return HTMLResponse("")  # Remove the row
    return {"status": "deleted"}
