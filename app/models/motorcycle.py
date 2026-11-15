import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Enum, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class MotorcycleStatus(str, enum.Enum):
    AVAILABLE = "available"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"


class Motorcycle(Base):
    __tablename__ = "motorcycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    engine_cc: Mapped[int] = mapped_column(Integer, nullable=False)
    location_address: Mapped[str] = mapped_column(String(200), nullable=False)
    hourly_rate: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[MotorcycleStatus] = mapped_column(
        Enum(MotorcycleStatus, name="motorcycle_status"),
        nullable=False,
        default=MotorcycleStatus.AVAILABLE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="motorcycle",
        cascade="all, delete-orphan",
    )
