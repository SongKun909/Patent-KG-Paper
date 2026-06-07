"""Patent schemas."""
from datetime import datetime
from pydantic import BaseModel


class PatentResponse(BaseModel):
    id: int
    filename: str
    lang: str
    page_count: int
    file_size: int
    is_scanned: bool
    uploaded_at: datetime
    metadata_: dict | None = None

    class Config:
        from_attributes = True
