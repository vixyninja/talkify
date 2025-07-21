import uuid as uuid_pkg
from typing import Annotated

from pydantic import BaseModel, Field


class Job(BaseModel):
    id: Annotated[uuid_pkg.UUID, Field(examples=["123e4567-e89b-12d3-a456-426614174000"])]
