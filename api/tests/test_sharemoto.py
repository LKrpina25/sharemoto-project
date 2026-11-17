from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from freezegun import freeze_time

from app.core.config import settings
from app.core.security import verify_password
from app.db.seed import seed_initial_data
from app.models.motorcycle import Motorcycle, MotorcycleStatus
from app.models.user import User, UserRole


def register_user(client, email: str, password: str = "securepassword123") -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Test Korisnik",
            "password": password,
        },
    )
    assert response.status_code == 201


def login(client, email: str, password: str = "securepassword123") -> dict:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def test_register_login_refresh_and_me(client):
    register_user(client, "test@sharemoto.com")
    tokens = login(client, "test@sharemoto.com")

    unknown_user = client.post(
        "/auth/login",
        json={"email": "missing@sharemoto.com", "password": "securepassword123"},
    )
    wrong_password = client.post(
        "/auth/login",
        json={"email": "test@sharemoto.com", "password": "incorrect"},
    )
    assert unknown_user.status_code == wrong_password.status_code == 401
    assert unknown_user.json() == wrong_password.json()

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "test@sharemoto.com"
    assert "hashed_password" not in me_response.json()

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]

    wrong_token_type = client.post(
        "/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )
    assert wrong_token_type.status_code == 401

    expired_token = jwt.encode(
        {
            "sub": "1",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    expired_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired_response.status_code == 401


def test_motorcycle_creation_requires_admin(client, db_session):
    hashed = bcrypt.hashpw(b"adminpass", bcrypt.gensalt()).decode("utf-8")
    admin = User(
        email="admin@moto.com",
        full_name="Glavni Admin",
        hashed_password=hashed,
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()
    admin_token = login(client, "admin@moto.com", "adminpass")["access_token"]

    register_user(client, "member@moto.com", "memberpass")
    member_token = login(client, "member@moto.com", "memberpass")["access_token"]
    motorcycle_data = {
        "brand": "Yamaha",
        "model_name": "MT-07",
        "engine_cc": 689,
        "location_address": "Zadar",
        "hourly_rate": 25.0,
    }

    denied = client.post(
        "/motorcycles/",
        headers={"Authorization": f"Bearer {member_token}"},
        json=motorcycle_data,
    )
    assert denied.status_code == 403

    created = client.post(
        "/motorcycles/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=motorcycle_data,
    )
    assert created.status_code == 201


@freeze_time("2026-06-01 10:00:00")
def test_reservation_ownership_rules_and_cancellation_deadline(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 48)
    hashed = bcrypt.hashpw(b"pass123", bcrypt.gensalt()).decode("utf-8")
    admin = User(
        email="adm@moto.com",
        full_name="Admin",
        hashed_password=hashed,
        role=UserRole.ADMIN,
    )
    member = User(
        email="mem@moto.com",
        full_name="Member",
        hashed_password=hashed,
        role=UserRole.MEMBER,
    )
    other_member = User(
        email="other@moto.com",
        full_name="Other",
        hashed_password=hashed,
        role=UserRole.MEMBER,
    )
    db_session.add_all([admin, member, other_member])
    db_session.commit()

    member_token = login(client, "mem@moto.com", "pass123")["access_token"]
    other_token = login(client, "other@moto.com", "pass123")["access_token"]
    admin_token = login(client, "adm@moto.com", "pass123")["access_token"]

    motorcycle_response = client.post(
        "/motorcycles/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "brand": "Kawasaki",
            "model_name": "Z650",
            "engine_cc": 649,
            "location_address": "Zadar",
            "hourly_rate": 20.0,
        },
    )
    motorcycle_id = motorcycle_response.json()["id"]
    starts_at = "2026-06-02T12:00:00Z"
    ends_at = "2026-06-02T15:00:00Z"
    reservation_data = {
        "motorcycle_id": motorcycle_id,
        "starts_at": starts_at,
        "ends_at": ends_at,
    }

    created = client.post(
        "/reservations/",
        headers={"Authorization": f"Bearer {member_token}"},
        json=reservation_data,
    )
    assert created.status_code == 201
    reservation_id = created.json()["id"]

    other_reservations = client.get(
        "/reservations/",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert other_reservations.status_code == 200
    assert other_reservations.json() == []

    denied_cancel = client.patch(
        f"/reservations/{reservation_id}/cancel",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert denied_cancel.status_code == 403

    overlap = client.post(
        "/reservations/",
        headers={"Authorization": f"Bearer {other_token}"},
        json=reservation_data,
    )
    assert overlap.status_code == 409
    assert overlap.json()["code"] == "RESERVATION_CONFLICT"
    assert "message" in overlap.json()

    with freeze_time("2026-06-02 10:00:00"):
        too_late = client.patch(
            f"/reservations/{reservation_id}/cancel",
            headers={"Authorization": f"Bearer {member_token}"},
        )
    assert too_late.status_code == 409
    assert too_late.json()["code"] == "CANCELLATION_DEADLINE_PASSED"

    with freeze_time("2026-06-02 08:00:00"):
        cancelled = client.patch(
            f"/reservations/{reservation_id}/cancel",
            headers={"Authorization": f"Bearer {member_token}"},
        )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    replacement = client.post(
        "/reservations/",
        headers={"Authorization": f"Bearer {member_token}"},
        json=reservation_data,
    )
    assert replacement.status_code == 201
    first_page = client.get(
        "/reservations/?limit=1&offset=0",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    second_page = client.get(
        "/reservations/?limit=1&offset=1",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert len(first_page.json()) == len(second_page.json()) == 1


def test_list_endpoints_support_pagination(client, db_session):
    for index in range(3):
        db_session.add(
            Motorcycle(
                brand=f"Brand{index}",
                model_name=f"Model{index}",
                engine_cc=500,
                location_address="Zadar",
                hourly_rate=20.0,
                status=MotorcycleStatus.AVAILABLE,
            )
        )
    db_session.commit()

    first_page = client.get("/motorcycles/?limit=2&offset=0")
    second_page = client.get("/motorcycles/?limit=2&offset=2")
    assert first_page.status_code == second_page.status_code == 200
    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 1
    assert client.get("/motorcycles/?limit=0").status_code == 422


def test_seed_is_idempotent(db_session, monkeypatch):
    monkeypatch.setattr(settings, "SEED_ADMIN_EMAIL", "seed-admin@sharemoto.com")
    monkeypatch.setattr(settings, "SEED_ADMIN_PASSWORD", "long-random-seed-password")

    seed_initial_data(db_session)
    seed_initial_data(db_session)

    assert db_session.query(Motorcycle).count() == 3
    admin = db_session.query(User).filter_by(email="seed-admin@sharemoto.com").one()
    assert admin.role == UserRole.ADMIN
    assert verify_password("long-random-seed-password", admin.hashed_password)
