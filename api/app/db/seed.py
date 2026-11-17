from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.motorcycle import Motorcycle, MotorcycleStatus
from app.models.reservation import Reservation
from app.models.user import User, UserRole

INITIAL_MOTORCYCLES = (
    {
        "brand": "Yamaha",
        "model_name": "MT-07",
        "engine_cc": 689,
        "location_address": "Zadar",
        "hourly_rate": 25.0,
    },
    {
        "brand": "Kawasaki",
        "model_name": "Z650",
        "engine_cc": 649,
        "location_address": "Split",
        "hourly_rate": 22.0,
    },
    {
        "brand": "Honda",
        "model_name": "CB500F",
        "engine_cc": 471,
        "location_address": "Zagreb",
        "hourly_rate": 20.0,
    },
)


def seed_initial_data(db: Session) -> None:
    if bool(settings.SEED_ADMIN_EMAIL) != bool(settings.SEED_ADMIN_PASSWORD):
        raise ValueError("SEED_ADMIN_EMAIL i SEED_ADMIN_PASSWORD moraju biti zadani zajedno.")

    if settings.SEED_ADMIN_EMAIL and settings.SEED_ADMIN_PASSWORD:
        admin = db.query(User).filter(User.email == settings.SEED_ADMIN_EMAIL).first()
        if admin is None:
            db.add(
                User(
                    email=settings.SEED_ADMIN_EMAIL,
                    full_name="ShareMoto administrator",
                    hashed_password=hash_password(settings.SEED_ADMIN_PASSWORD),
                    role=UserRole.ADMIN,
                )
            )

    for motorcycle_data in INITIAL_MOTORCYCLES:
        motorcycle = (
            db.query(Motorcycle)
            .filter(
                Motorcycle.brand == motorcycle_data["brand"],
                Motorcycle.model_name == motorcycle_data["model_name"],
            )
            .first()
        )
        if motorcycle is None:
            db.add(
                Motorcycle(
                    **motorcycle_data,
                    status=MotorcycleStatus.AVAILABLE,
                )
            )
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed_initial_data(db)


if __name__ == "__main__":
    main()
