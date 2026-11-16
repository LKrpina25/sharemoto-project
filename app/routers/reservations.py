from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.session import get_db
from app.models.reservation import Reservation, ReservationStatus
from app.models.motorcycle import Motorcycle, MotorcycleStatus
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.routers.motorcycles import get_current_user

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.post("/", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_reservation(
    res_data: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Parsiranje stringova u datetime objekte
    try:
        starts_at = datetime.fromisoformat(res_data.starts_at.replace("Z", "+00:00"))
        ends_at = datetime.fromisoformat(res_data.ends_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Neispravan format datuma i vremena. Koristite ISO format.",
        )

    # Provjera valjanosti datuma
    if starts_at >= ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vrijeme završetka mora biti nakon vremena početka.",
        )

    if starts_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nije moguće rezervirati termin u prošlosti.",
        )

    # Provjera postoji li motocikl i je li dostupan
    motorcycle = db.query(Motorcycle).filter(Motorcycle.id == res_data.motorcycle_id).first()
    if not motorcycle:
        raise HTTPException(status_code=404, detail="Motocikl nije pronađen.")
    
    if motorcycle.status != MotorcycleStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Motocikl trenutno nije dostupan za rezervaciju.",
        )

    # Provjera preklapanja termina (postojeće potvrđene rezervacije za isti motocikl)
    overlapping = db.query(Reservation).filter(
        Reservation.motorcycle_id == res_data.motorcycle_id,
        Reservation.status == ReservationStatus.CONFIRMED,
        and_(
            Reservation.starts_at < ends_at,
            Reservation.ends_at > starts_at,
        ),
    ).first()

    if overlapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Motocikl je već rezerviran u odabranom terminu.",
        )

    new_reservation = Reservation(
        user_id=current_user.id,
        motorcycle_id=res_data.motorcycle_id,
        starts_at=starts_at,
        ends_at=ends_at,
        status=ReservationStatus.CONFIRMED,
    )
    db.add(new_reservation)
    db.commit()
    db.refresh(new_reservation)
    return new_reservation


@router.get("/", response_model=list[ReservationResponse])
def get_my_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value == "admin":
        return db.query(Reservation).all()
    return db.query(Reservation).filter(Reservation.user_id == current_user.id).all()


@router.patch("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena.")

    if reservation.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nemate ovlasti za otkazivanje ove rezervacije.",
        )

    if reservation.status != ReservationStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ova rezervacija se više ne može otkazati.",
        )

    # Pravilo: Minimalni rok za otkazivanje je 3 sata prije početka
    starts_at = reservation.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)

    time_limit = starts_at - timedelta(hours=3)
    now = datetime.now(timezone.utc)

    if now > time_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rezervaciju je moguće otkazati najkasnije 3 sata prije početka termina.",
        )

    reservation.status = ReservationStatus.CANCELLED
    db.commit()
    db.refresh(reservation)
    return reservation
