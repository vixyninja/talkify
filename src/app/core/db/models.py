import uuid as uuid_pkg
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    """Mixin for UUID primary key.
    This mixin adds a UUID primary key to the model.
    - `id`: UUID primary key field.
    Copy this mixin to any model that requires a UUID primary key.
    """

    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))


class TimestampMixin:
    """Mixin for timestamp fields.
    This mixin adds `created_at` and `updated_at` fields to the model.
    - `created_at`: Timestamp when the record was created. (timestamp)
    - `updated_at`: Timestamp when the record was last updated. (timestamp)
    Copy this mixin to any model that requires timestamp functionality.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(UTC), server_default=text("current_timestamp(0)")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC), server_default=text("current_timestamp(0)")
    )


class SoftDeleteMixin:
    """Mixin for soft deletion of records.
    This mixin adds `deleted_at` and `is_deleted` fields to the model.
    - `deleted_at`: Timestampz when the record was soft deleted. (timestamptz)
    - `is_deleted`: Boolean flag indicating if the record is deleted.
    Copy this mixin to any model that requires soft deletion functionality.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class I18nKeyValues(str, Enum):
    """Enum representing internationalization keys for default values."""

    CONVERSATIONS_DEFAULT_NAME = "conversations.default_name"
    CONVERSATIONS_DEFAULT_DESCRIPTION = "conversations.default_description"
