from datetime import datetime
from sqlalchemy import Text, ForeignKey, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"), unique=True, nullable=False)
    goals: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    action_items: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    decisions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    thread: Mapped["Thread"] = relationship(back_populates="plan")  # noqa: F821
