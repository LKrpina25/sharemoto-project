from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.reservation import ReservationStatus
from app.schemas.motorcycle import MotorcycleResponse


class ReservationCreate(BaseModel):
    motorcycle_id: int
    starts_at: str
    ends_at: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ReservationResponse(BaseModel):
    id: int
    user_id: int
    motorcycle_id: int
    starts_at: datetime
    ends_at: datetime
    status: ReservationStatus
    created_at: datetime
    motorcycle: MotorcycleResponse | None = None

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
