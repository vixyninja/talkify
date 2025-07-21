import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class ConversationMembers(Base):
    __tablename__ = "conversation_members"

    # Relationship fields
    conversation_id: Mapped[str] = mapped_column("conversation_id", nullable=False, index=True)
    user_id: Mapped[str] = mapped_column("user_id", nullable=False, index=True)

    # Primary key
    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))

    # Business logic fields
    is_admin: Mapped[bool] = mapped_column(default=False, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Timestamp and soft delete fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), server_default=text("current_timestamp(0)")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), onupdate=datetime.now(UTC), server_default=text("current_timestamp(0)")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
