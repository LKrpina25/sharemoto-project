from datetime import datetime, timedelta, timezone
from freezegun import freeze_time
from app.models.user import UserRole
from app.models.motorcycle import MotorcycleStatus


def test_register_and_login(client):
    # Registracija
    response = client.post(
        "/auth/register",
        json={
            "email": "test@sharemoto.com",
            "full_name": "Test Korisnik",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@sharemoto.com"
    assert data["role"] == "member"

    # Prijava
    response = client.post(
        "/auth/login",
        json={
            "email": "test@sharemoto.com",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


def create_test_user_and_token(client, email="admin@sharemoto.com", role=UserRole.MEMBER):
    client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Admin User" if role == UserRole.ADMIN else "Member User",
            "password": "password123",
        },
    )
    # Ako želimo da bude admin, možemo direktno u bazi prebaciti ulogu (ili simulirati)
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    return response.json()["access_token"]


def test_motorcycle_creation_permissions(client, db_session):
    # Ručno stvaramo admina u bazi za potrebe testa
    from app.models.user import User
    import bcrypt

    hashed = bcrypt.hashpw(b"adminpass", bcrypt.gensalt()).decode("utf-8")
    admin_user = User(email="admin@moto.com", full_name="Glavni Admin", hashed_password=hashed, role=UserRole.ADMIN)
    db_session.add(admin_user)
    db_session.commit()

    # Prijava admina
    login_res = client.post("/auth/login", json={"email": "admin@moto.com", "password": "adminpass"})
    admin_token = login_res.json()["access_token"]

    # Admin kreira motocikl
    moto_res = client.post(
        "/motorcycles/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "brand": "Yamaha",
            "model_name": "MT-07",
            "engine_cc": 689,
            "location_address": "Zadar, Poluotok",
            "hourly_rate": 25.0,
            "status": "available",
        },
    )
    assert moto_res.status_code == 201
    assert moto_res.json()["brand"] == "Yamaha"


@freeze_time("2026-06-01 10:00:00")
def test_reservation_and_cancellation_rules(client, db_session):
    # 1. Priprema: Kreiramo admina i motocikl
    from app.models.user import User
    import bcrypt

    hashed = bcrypt.hashpw(b"pass123", bcrypt.gensalt()).decode("utf-8")
    admin = User(email="adm@moto.com", full_name="Admin", hashed_password=hashed, role=UserRole.ADMIN)
    member = User(email="mem@moto.com", full_name="Member", hashed_password=hashed, role=UserRole.MEMBER)
    db_session.add_all([admin, member])
    db_session.commit()

    # Prijavljujemo člana da dobijemo token
    member_login = client.post("/auth/login", json={"email": "mem@moto.com", "password": "pass123"})
    member_token = member_login.json()["access_token"]

    # Admin dodaje motocikl
    admin_login = client.post("/auth/login", json={"email": "adm@moto.com", "password": "pass123"})
    admin_token = admin_login.json()["access_token"]

    moto_res = client.post(
        "/motorcycles/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "brand": "Kawasaki",
            "model_name": "Z650",
            "engine_cc": 649,
            "location_address": "Zadar",
            "hourly_rate": 20.0,
            "status": "available",
        },
    )
    moto_id = moto_res.json()["id"]

    # 2. Kreiramo rezervaciju za sutra (2026-06-02 od 12:00 do 15:00)
    starts = "2026-06-02T12:00:00Z"
    ends = "2026-06-02T15:00:00Z"

    res_response = client.post(
        "/reservations/",
        headers={"Authorization": f"Bearer {member_token}"},
        json={
            "motorcycle_id": moto_id,
            "starts_at": starts,
            "ends_at": ends,
        },
    )
    assert res_response.status_code == 201
    reservation_id = res_response.json()["id"]
# 3. Testiramo pravilo otkazivanja:
    # Ako pokušamo otkazati 2 sata prije početka (zaleđeno vrijeme: 2026-06-02 u 10:00, a početak je u 12:00),
    # sustav MORA odbiti otkazivanje jer je manje od 3 sata!
    with freeze_time("2026-06-02 10:00:00"):
        cancel_fail = client.patch(
            f"/reservations/{reservation_id}/cancel",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert cancel_fail.status_code == 400

    # Ako otkazujemo 4 sata prije početka (zaleđeno vrijeme: 2026-06-02 u 08:00, početak u 12:00),
    # otkazivanje MORA uspjeti!
    with freeze_time("2026-06-02 08:00:00"):
        cancel_success = client.patch(
            f"/reservations/{reservation_id}/cancel",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert cancel_success.status_code == 200
        assert cancel_success.json()["status"] == "cancelled"
