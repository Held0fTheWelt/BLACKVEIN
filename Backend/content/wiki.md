# World of Shadows – Wiki

Willkommen im Wiki zu **World of Shadows** (Blackveign).

## Über das Projekt

World of Shadows ist ein Flask-basiertes Backend mit API, Authentifizierung, News-System und E-Mail-Verifikation. Das Frontend konsumiert die API; Login, Registrierung und Dashboard werden vom Backend bereitgestellt.

## Inhalte

- **News:** Veröffentlichte Artikel unter `/news` (bzw. Frontend) und über die API `GET /api/v1/news`.
- **Registrierung & Login:** E-Mail-Verifikation (Aktivierungs-Link) ist aktiv; ohne Verifikation ist der Login gesperrt.
- **User & Rollen:** Rollen `user`, `editor`, `admin`. Editor/Admin können News erstellen und bearbeiten; Admin hat Zugriff auf die User-Verwaltung (CRUD über die API).

## Technik

- **Backend:** Flask, SQLAlchemy, Flask-Migrate, JWT (API), Session (Web), Flask-Mail.
- **API-Dokumentation:** Siehe `docs/BackendApi.md`.
- **Runbook:** Siehe `docs/runbook.md` für lokale Befehle (PowerShell und Bash, `flask` und `python -m flask`).

---

*Dieses Wiki wird aus der Markdown-Datei `Backend/content/wiki.md` generiert.*
