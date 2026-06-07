"""Patent routes: upload, import, list, delete."""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.patent import Patent
from app.schemas.patent import PatentResponse
from app.config import settings

router = APIRouter(prefix="/api/patents", tags=["patents"])


@router.get("/", response_model=dict)
def list_patents(
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
    return {
        "items": [PatentResponse.model_validate(p) for p in items],
        "total": total,
        "page": page,
    }


@router.post("/upload", response_model=PatentResponse)
async def upload_patent(
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
    return PatentResponse.model_validate(patent)


@router.post("/import", response_model=dict)
def import_from_directory(
    directory: str = Query(...),
    db: Session = Depends(get_db),
):
    """Bulk import PDFs from a server directory."""
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
            filename=fname,
            file_path=fpath,
            lang=lang,
            file_size=os.path.getsize(fpath),
        )
        db.add(patent)
        imported += 1
    db.commit()
    return {"imported": imported}


@router.delete("/{patent_id}", response_model=dict)
def delete_patent(patent_id: int, db: Session = Depends(get_db)):
    patent = db.query(Patent).filter(Patent.id == patent_id).first()
    if not patent:
        raise HTTPException(404, "Patent not found")
    db.delete(patent)
    db.commit()
    return {"status": "deleted"}
