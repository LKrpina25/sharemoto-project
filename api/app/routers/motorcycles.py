from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin
from app.db.session import get_db
from app.models.motorcycle import Motorcycle, MotorcycleStatus
from app.models.user import User
from app.schemas.motorcycle import MotorcycleCreate, MotorcycleUpdate, MotorcycleResponse

router = APIRouter(prefix="/motorcycles", tags=["Motorcycles"])


@router.get("/", response_model=list[MotorcycleResponse])
def get_motorcycles(
    status_filter: MotorcycleStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Motorcycle)
    if status_filter:
        query = query.filter(Motorcycle.status == status_filter)
    return query.order_by(Motorcycle.id).offset(offset).limit(limit).all()


@router.get("/{motorcycle_id}", response_model=MotorcycleResponse)
def get_motorcycle(motorcycle_id: int, db: Session = Depends(get_db)):
    motorcycle = db.query(Motorcycle).filter(Motorcycle.id == motorcycle_id).first()
    if not motorcycle:
        raise HTTPException(status_code=404, detail="Motocikl nije pronađen.")
    return motorcycle


@router.post("/", response_model=MotorcycleResponse, status_code=status.HTTP_201_CREATED)
def create_motorcycle(
    moto_data: MotorcycleCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    new_moto = Motorcycle(**moto_data.model_dump())
    db.add(new_moto)
    db.commit()
    db.refresh(new_moto)
    return new_moto


@router.patch("/{motorcycle_id}", response_model=MotorcycleResponse)
def update_motorcycle(
    motorcycle_id: int,
    moto_update: MotorcycleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    motorcycle = db.query(Motorcycle).filter(Motorcycle.id == motorcycle_id).first()
    if not motorcycle:
        raise HTTPException(status_code=404, detail="Motocikl nije pronađen.")

    update_data = moto_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(motorcycle, key, value)

    db.commit()
    db.refresh(motorcycle)
    return motorcycle


@router.delete("/{motorcycle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_motorcycle(
    motorcycle_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    motorcycle = db.query(Motorcycle).filter(Motorcycle.id == motorcycle_id).first()
    if not motorcycle:
        raise HTTPException(status_code=404, detail="Motocikl nije pronađen.")

    db.delete(motorcycle)
    db.commit()
    return None
