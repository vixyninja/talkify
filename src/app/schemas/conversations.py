import uuid as uuid_pkg
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ..core.schemas import PersistentDeletion, TimestampSchema, UUIDSchema
from ..models.conversations import ConversationType


class ConversationsBase(BaseModel):
    type: Annotated[str, Field(examples=[ConversationType.__list__])]


class Conversations(TimestampSchema, ConversationsBase, UUIDSchema, PersistentDeletion):
    name: Annotated[str, Field(min_length=1, max_length=100, examples=["General Discussion"])]
    description: Annotated[str | None, Field(max_length=500, examples=["A general topics."], default=None)]


class ConversationRead(BaseModel):
    id: Annotated[uuid_pkg.UUID, Field(examples=["123e4567-e89b-12d3-a456-426614174000"])]
    type: Annotated[str, Field(examples=[ConversationType.__list__])]
    name: Annotated[str, Field(min_length=1, max_length=100, examples=["General Discussion"])]
    description: Annotated[str | None, Field(max_length=500, examples=["A general topics."], default=None)]


class ConversationCreate(ConversationsBase):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, Field(min_length=1, max_length=100, examples=["General Discussion"])]
    description: Annotated[str | None, Field(max_length=500, examples=["A general topics."], default=None)]


class ConversationCreateInternal(ConversationCreate):
    pass


class ConversationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str | None, Field(min_length=1, max_length=100, examples=["Updated Discussion"], default=None)]
    description: Annotated[str | None, Field(max_length=500, examples=["Updated description"], default=None)]


class ConversationUpdateInternal(ConversationUpdate):
    updated_at: datetime


class ConversationDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_deleted: bool
    deleted_at: datetime


class ConversationRestoreDelete(BaseModel):
    is_deleted: bool = False
