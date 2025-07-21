import uuid as uuid_pkg
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base
from ..core.db.models import I18nKeyValues


class ConversationType(str, Enum):
    """Enum representing different types of conversations.
    - PRIVATE: A private conversation between two users.
    - GROUP: A group conversation with multiple users.
    - CHANNEL: A channel conversation, typically with a larger audience.
    - SYSTEM: A system conversation, often used for notifications or alerts.
    - BOT: A conversation with a bot or automated system.
    """

    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"
    SYSTEM = "system"
    BOT = "bot"

    def __list__(self) -> list[str]:
        """Return a list of all conversation types."""
        return [type_.value for type_ in ConversationType]


class Conversations(Base):
    __tablename__ = "conversations"

    # Primary key
    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))

    # Business logic fields
    type: Mapped[ConversationType] = mapped_column(
        SqlEnum(ConversationType, name="conversation_type"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=I18nKeyValues.CONVERSATIONS_DEFAULT_NAME.value
    )
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True, default=I18nKeyValues.CONVERSATIONS_DEFAULT_DESCRIPTION.value
    )

    # Timestamp and soft delete fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC), server_default=text("current_timestamp(0)")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(UTC),
        onupdate=datetime.now(UTC),
        server_default=text("current_timestamp(0)"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
