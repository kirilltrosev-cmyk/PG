from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin
from app.models.enums import CompletionStatus, TaskStatus, TaskType


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(32), index=True)
    target_url: Mapped[str] = mapped_column(String(512))
    target_chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reward: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_limit: Mapped[int] = mapped_column(default=1)
    completed_count: Mapped[int] = mapped_column(default=0)
    audience_type: Mapped[str] = mapped_column(String(32), default="all")
    filters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.MODERATION.value, index=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class TaskCompletion(TimestampMixin, Base):
    __tablename__ = "task_completions"
    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_task_once_per_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=CompletionStatus.PENDING.value)
    proof_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reward: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    checked_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
