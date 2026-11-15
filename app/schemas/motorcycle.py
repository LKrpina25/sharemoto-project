from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.motorcycle import MotorcycleStatus


class MotorcycleCreate(BaseModel):
    brand: str = Field(..., min_length=1, max_length=50)
    model_name: str = Field(..., min_length=1, max_length=100)
    engine_cc: int = Field(..., gt=0)
    location_address: str = Field(..., min_length=3, max_length=200)
    hourly_rate: float = Field(..., gt=0)
    status: MotorcycleStatus = MotorcycleStatus.AVAILABLE

    model_config = ConfigDict(protected_namespaces=())


class MotorcycleUpdate(BaseModel):
    brand: str | None = Field(None, min_length=1, max_length=50)
    model_name: str | None = Field(None, min_length=1, max_length=100)
    engine_cc: int | None = Field(None, gt=0)
    location_address: str | None = Field(None, min_length=3, max_length=200)
    hourly_rate: float | None = Field(None, gt=0)
    status: MotorcycleStatus | None = None

    model_config = ConfigDict(protected_namespaces=())


class MotorcycleResponse(BaseModel):
    id: int
    brand: str
    model_name: str
    engine_cc: int
    location_address: str
    hourly_rate: float
    status: MotorcycleStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
