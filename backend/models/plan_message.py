from datetime import datetime
from sqlalchemy import Text, ForeignKey, String, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base


class PlanMessage(Base):
    __tablename__ = "plan_messages"
    __table_args__ = (Index("ix_plan_messages_thread", "thread_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User | None"] = relationship()  # noqa: F821
