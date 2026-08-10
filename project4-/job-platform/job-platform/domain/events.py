from pydantic import BaseModel


class EventView(BaseModel):
    id: int
    event_type: str
    data: dict

    model_config = {"from_attributes": True}
