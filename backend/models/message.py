from datetime import datetime
from sqlalchemy import Text, ForeignKey, Boolean, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.base import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_thread_created", "thread_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    thread: Mapped["Thread"] = relationship(back_populates="messages")  # noqa: F821
    user: Mapped["User | None"] = relationship(back_populates="messages")  # noqa: F821
