"""Task model with state machine."""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patent_id: Mapped[int] = mapped_column(ForeignKey("patents.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patent = relationship("Patent", back_populates="tasks")

    VALID_STATUSES = [
        "pending", "queued", "running", "completed",
        "paused", "cancelled", "failed",
    ]
    PAUSABLE_STATUSES = ["running"]
    CANCELLABLE_STATUSES = ["pending", "queued", "running", "paused"]
    RESUMABLE_STATUSES = ["paused"]
    RETRYABLE_STATUSES = ["failed"]
    TERMINAL_STATUSES = ["completed", "cancelled"]
