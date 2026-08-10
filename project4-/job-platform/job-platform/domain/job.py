from pydantic import BaseModel, Field
from typing import Literal


TaskType = Literal["calculate", "slow", "fail"]


class JobCreate(BaseModel):
    task: TaskType
    number: int = Field(ge=0, le=1_000_000)
    priority: int = Field(default=5, ge=1, le=10)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)


class JobView(BaseModel):
    id: str
    task: str
    status: str
    priority: int
    timeout_seconds: int
    result: dict | None = None
    last_error: str | None = None

    model_config = {"from_attributes": True}
