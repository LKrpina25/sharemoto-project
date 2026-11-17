from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.dependencies import get_current_user
from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.reservation import Reservation, ReservationStatus
from app.models.motorcycle import Motorcycle, MotorcycleStatus
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationResponse

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

    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=timezone.utc)

    # Provjera valjanosti datuma
    if starts_at >= ends_at:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_RESERVATION_TIME",
            message="Vrijeme završetka mora biti nakon vremena početka.",
        )

    if starts_at < datetime.now(timezone.utc):
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="RESERVATION_IN_PAST",
            message="Nije moguće rezervirati termin u prošlosti.",
        )

    # Provjera postoji li motocikl i je li dostupan
    motorcycle = db.query(Motorcycle).filter(Motorcycle.id == res_data.motorcycle_id).first()
    if not motorcycle:
        raise HTTPException(status_code=404, detail="Motocikl nije pronađen.")
    
    if motorcycle.status != MotorcycleStatus.AVAILABLE:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="MOTORCYCLE_UNAVAILABLE",
            message="Motocikl trenutno nije dostupan za rezervaciju.",
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
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="RESERVATION_CONFLICT",
            message="Motocikl je već rezerviran u odabranom terminu.",
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
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Reservation)
    if current_user.role.value != "admin":
        query = query.filter(Reservation.user_id == current_user.id)
    return query.order_by(Reservation.id).offset(offset).limit(limit).all()


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
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="RESERVATION_NOT_CANCELLABLE",
            message="Ova rezervacija se više ne može otkazati.",
        )

    # Pravilo: Minimalni rok za otkazivanje je 3 sata prije početka
    starts_at = reservation.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)

    time_limit = starts_at - timedelta(hours=3)
    now = datetime.now(timezone.utc)

    if now > time_limit:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="CANCELLATION_DEADLINE_PASSED",
            message="Rezervaciju je moguće otkazati najkasnije 3 sata prije početka termina.",
        )

    reservation.status = ReservationStatus.CANCELLED
    db.commit()
    db.refresh(reservation)
    return reservation
