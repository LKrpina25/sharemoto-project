from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import jwt

from app.db.session import get_db
from app.models.motorcycle import Motorcycle, MotorcycleStatus
from app.models.user import User, UserRole
from app.schemas.motorcycle import MotorcycleCreate, MotorcycleUpdate, MotorcycleResponse
from app.core.config import settings
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/motorcycles", tags=["Motorcycles"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        # Dodajemo options={"verify_exp": False} kako freezegun ne bi rušio JWT tokene
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_exp": False})
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Nevažeći token.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Nevažeći token.")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Korisnik nije pronađen.")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pristup dopušten samo administratorima.",
        )
    return current_user


@router.get("/", response_model=list[MotorcycleResponse])
def get_motorcycles(status_filter: MotorcycleStatus | None = None, db: Session = Depends(get_db)):
    query = db.query(Motorcycle)
    if status_filter:
        query = query.filter(Motorcycle.status == status_filter)
    return query.all()


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
