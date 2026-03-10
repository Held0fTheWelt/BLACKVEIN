# Runbook — Local development

**Befehle:** Jeweils zuerst die **Kurzform** (z. B. `flask`), danach die **Python-Form** (`python -m flask`), damit sie in jeder Umgebung funktionieren. Unter **PowerShell** Zeilen mit `;` trennen oder eine Zeile pro Befehl; Umgebungsvariablen mit `$env:NAME = "value"`. Unter **Bash/Terminal** `export NAME=value` und bei Mehrzeilern `\` am Zeilenende.

---

## One-time setup

**Bash / Terminal (z. B. Git Bash, WSL, macOS/Linux):**

```bash
cd Backend
pip install -r requirements.txt
cp ../.env.example ../.env
# .env bearbeiten: SECRET_KEY und JWT_SECRET_KEY setzen (oder DEV_SECRETS_OK=1 für Dev-Fallbacks)
# FLASK_APP=run:app in .env eintragen oder exportieren
flask init-db
# bzw. mit Python explizit:
python -m flask init-db

# Migrationen anwenden (falls vorhanden):
flask db upgrade
# bzw.:
python -m flask db upgrade

# Optional, nur wenn DEV_SECRETS_OK=1:
flask seed-dev-user --generate
# bzw.:
python -m flask seed-dev-user --generate
# Oder: SEED_DEV_USERNAME/SEED_DEV_PASSWORD setzen oder --username/--password angeben
```

**PowerShell (Windows):**

```powershell
cd Backend
pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env
# .env bearbeiten: SECRET_KEY und JWT_SECRET_KEY (oder DEV_SECRETS_OK=1)
# FLASK_APP=run:app in .env eintragen oder: $env:FLASK_APP = "run:app"

flask init-db
# bzw. mit Python explizit:
python -m flask init-db

# Migrationen anwenden:
flask db upgrade
# bzw.:
python -m flask db upgrade

# Optional (DEV_SECRETS_OK=1):
flask seed-dev-user --generate
# bzw.:
python -m flask seed-dev-user --generate
```

---

## Server starten

**Bash / Terminal:**

```bash
cd Backend
export FLASK_APP=run:app
export FLASK_DEBUG=1
python run.py
# Oder mit Flask-CLI:
flask run --port 5000
# bzw.:
python -m flask run --port 5000
```

**PowerShell:**

```powershell
cd Backend
$env:FLASK_APP = "run:app"
$env:FLASK_DEBUG = "1"
python run.py
# Oder mit Flask-CLI:
flask run --port 5000
# bzw.:
python -m flask run --port 5000
```

Server: http://127.0.0.1:5000

---

## Weitere nützliche Befehle (Backend)

| Aktion | Kurzform | Mit Python |
|--------|----------|------------|
| Migrationen anwenden | `flask db upgrade` | `python -m flask db upgrade` |
| Neue Migration anlegen | `flask db revision -m "Beschreibung"` | `python -m flask db revision -m "Beschreibung"` |
| Migrationsstand anzeigen | `flask db current` | `python -m flask db current` |
| Revision als erledigt markieren (ohne ausführen) | `flask db stamp 006_evt` | `python -m flask db stamp 006_evt` |
| Dev-User anlegen | `flask seed-dev-user --username dev --password Pass1` | `python -m flask seed-dev-user --username dev --password Pass1` |
| Beispiel-News anlegen | `flask seed-news` | `python -m flask seed-news` |
| Tests ausführen | `pytest tests` | `python -m pytest tests` |
| Tests ohne Coverage | `pytest tests --no-cov` | `python -m pytest tests --no-cov` |

**PowerShell:** Alle Befehle aus dem Backend-Verzeichnis (`cd Backend`) ausführen; bei mehreren Befehlen mit `;` trennen, z. B. `cd Backend; python -m flask db upgrade`.

---

## Web flow

1. http://127.0.0.1:5000/ im Browser öffnen.
2. „Log in“ → Benutzername/Passwort (z. B. vom seed-dev-user) eingeben.
3. Nach dem Login Weiterleitung auf /dashboard.
4. „Log out“ (Button im Header) → POST zum Logout.

---

## API flow (Beispiel)

**Bash / Terminal:**

```bash
# 1. Registrieren (oder bestehenden User nutzen)
curl -X POST http://127.0.0.1:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"Alice123"}'

# 2. Login, Token aus Response holen
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"Alice123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Geschützte Route aufrufen
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/auth/me
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/test/protected
```

**PowerShell:**

```powershell
# 1. Registrieren
curl.exe -X POST http://127.0.0.1:5000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"alice\",\"email\":\"alice@example.com\",\"password\":\"Alice123\"}'

# 2. Login, Token in Variable
$response = curl.exe -s -X POST http://127.0.0.1:5000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"alice\",\"password\":\"Alice123\"}'
$TOKEN = ( $response | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])" )

# 3. Geschützte Route
curl.exe -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/auth/me
curl.exe -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/test/protected
```

---

## Health checks

- **Web:** `GET /health` → JSON `{"status":"ok"}` (unauthenticated).
- **API:** `GET /api/v1/health` → JSON `{"status":"ok"}` (unauthenticated).

---

## Fehler & Limits

- **Web-Routen** (z. B. `/`, `/login`, `/dashboard`): 404/500 als HTML (Templates).
- **API-Routen** (unter `/api/`): 404, 429, 500 und JWT-401 als JSON `{"error": "..."}`.
- **Rate Limit:** 429 als JSON; Standard aus `RATELIMIT_DEFAULT`.

---

## Troubleshooting

- **SECRET_KEY must be set:** In `.env` `SECRET_KEY` und `JWT_SECRET_KEY` setzen, oder für lokale Dev `DEV_SECRETS_OK=1`.
- **CSRF invalid on login:** Login-Formular muss CSRF-Token enthalten (in den Templates bereits vorhanden).
- **CORS-Fehler vom Frontend:** In `.env` `CORS_ORIGINS` auf die Frontend-Origin setzen (z. B. `http://localhost:3000`).
- **PowerShell: „&&“ unbekannt:** Unter PowerShell Befehle mit `;` trennen (z. B. `cd Backend; python -m flask db upgrade`) oder pro Befehl eine Zeile.
- **flask: Befehl nicht gefunden:** Statt `flask` immer `python -m flask` verwenden (aus dem Backend-Verzeichnis).
