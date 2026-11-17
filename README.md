# ShareMoto – 1. dio projekta

Backend aplikacije za rezervaciju motocikala izrađen je pomoću FastAPI-ja,
SQLAlchemyja 2, Alembica i PostgreSQL-a.

## Preduvjeti

- Python 3.11 ili noviji
- Docker Desktop i Docker Compose

## Lokalno pokretanje (Windows PowerShell)

Naredbe izvodite iz korijena repozitorija.

1. Napravite lokalnu konfiguraciju i promijenite administratorsku lozinku i
   `SECRET_KEY` na vlastite, dovoljno jake vrijednosti:

   ```powershell
   Copy-Item .env.example .env
   ```

   U `.env` postavite `SEED_ADMIN_EMAIL` i `SEED_ADMIN_PASSWORD` na vlastite
   vrijednosti. `.env` se ne predaje u repozitorij.

2. Pokrenite PostgreSQL:

   ```powershell
   docker compose up -d
   ```

3. Instalirajte ovisnosti i aktivirajte virtualno okruženje:

   ```powershell
   Set-Location api
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

4. Izvedite migracije i inicijalne podatke:

   ```powershell
   python -m alembic upgrade head
   python -m app.db.seed
   ```

   Skripta za početne podatke može se sigurno pokrenuti više puta. Motocikli se
   dodaju samo ako ne postoje, a početni administrator se kreira samo ako njegov
   email još nije zauzet.

5. Pokrenite API:

   ```powershell
   uvicorn app.main:app --reload
   ```

   Dokumentacija API-ja dostupna je na `http://127.0.0.1:8000/docs`.

## Testovi

Iz mape `api/`, uz aktivirano virtualno okruženje, pokrenite:

```powershell
python -m pytest -q
```

Testovi koriste izoliranu SQLite bazu u memoriji, pa ne zahtijevaju pokrenut
PostgreSQL.

## Važne krajnje točke

- `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`
- `/motorcycles`: popis, detalji i administratorsko upravljanje motociklima
- `/reservations`: kreiranje, popis vlastitih rezervacija i otkazivanje

Zaštićene krajnje točke koriste Bearer access token. Popisi podržavaju `limit`
(1–100, zadano 20) i `offset` (zadano 0).
