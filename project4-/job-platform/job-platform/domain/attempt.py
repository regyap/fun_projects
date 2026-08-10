from pydantic import BaseModel


class AttemptView(BaseModel):
    id: str
    attempt_number: int
    worker_id: str
    status: str
    error: str | None = None
    result: dict | None = None

    model_config = {"from_attributes": True}
