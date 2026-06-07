"""Extracted quintuple result."""
from datetime import datetime
from sqlalchemy import String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Quintuple(Base):
    __tablename__ = "quintuples"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patent_id: Mapped[int] = mapped_column(ForeignKey("patents.id", ondelete="CASCADE"))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    value: Mapped[str] = mapped_column(String(300), default="")
    relation: Mapped[str] = mapped_column(String(100), default="")
    object: Mapped[str] = mapped_column(String(300), default="")
    condition: Mapped[str] = mapped_column(String(500), default="")
    source_text: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patent = relationship("Patent", back_populates="quintuples")
