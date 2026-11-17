# Izvještaj o funkcionalnosti – ShareMoto, 1. dio

ShareMoto je backend aplikacija za pregled motocikala i upravljanje njihovim
rezervacijama. Implementiran je pomoću FastAPI-ja, SQLAlchemyja 2 i
PostgreSQL-a; promjene sheme baze upravlja Alembic.

Korisnici se registriraju i prijavljuju, a lozinke se pohranjuju kao bcrypt
hash. API izdaje JWT pristupni i refresh token te nudi `/auth/login`,
`/auth/refresh` i `/auth/me`. Sustav razlikuje člana i administratora:
administratorsko upravljanje motociklima zaštićeno je ulogom, a član vidi i
mijenja samo vlastite rezervacije.

Poslovna pravila sprječavaju rezervaciju motocikla izvan dostupnog statusa,
termina u prošlosti i preklapanja rezervacija. Potvrđena rezervacija može se
otkazati najkasnije tri sata prije početka. Popisi podržavaju `limit` i
`offset`, a greške poslovnih pravila vraćaju kod i poruku.

Početni podaci mogu se inicijalizirati ponovljivom seed skriptom. Testovi
pokrivaju autentikaciju, ovlasti, vlasništvo, poslovna pravila, straničenje i
ponovljivost početnih podataka.

Javni Git repozitorij: https://github.com/LKrpina25/sharemoto-project

Ovaj izvještaj odnosi se samo na 1. dio projekta – backend.
