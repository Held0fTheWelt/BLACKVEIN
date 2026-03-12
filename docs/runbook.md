# Runbook — Local development

Das Runbook ist für **Linux (Bash/Terminal)**, **Windows (PowerShell)** und **PyCharm** gedacht. Jeder Befehl erscheint in **zwei Zeilen**: <span style="color:#0a0">**Kurzform**</span> (z. B. `flask`) und <span style="color:#00a">**Python -m**</span> (`python -m flask` usw.) — **nur eine der beiden Zeilen ausführen**.

- **Linux:** `export NAME=value`; bei mehrzeiligen Befehlen `\` am Zeilenende.
- **PowerShell:** Zeilen mit `;` trennen oder ein Befehl pro Zeile; Umgebungsvariablen mit `$env:NAME = "value"`.
- **PyCharm:** Run Configurations (siehe unten) oder integriertes Terminal mit Working Directory `Backend`; `.env` im Projektroot wird oft automatisch geladen.

---

## One-time setup

**Linux (Bash / Terminal):**  
*Erste Zeile = Kurzform, zweite Zeile = Python -m — pro Aktion nur eine ausführen.*

```bash
cd Backend
pip install -r requirements.txt
python -m pip install -r requirements.txt
cp ../.env.example ../.env
# .env bearbeiten: SECRET_KEY, JWT_SECRET_KEY (oder DEV_SECRETS_OK=1); FLASK_APP=run:app
flask init-db
python -m flask init-db
# Bei Migrations-only-Workflow (ohne init-db):
flask db upgrade
python -m flask db upgrade
# Falls nach init-db "table already exists": nur eine Zeile ausführen:
flask db stamp head
python -m flask db stamp head
# Optional (DEV_SECRETS_OK=1) – Dev-User (Moderator):
flask seed-dev-user --generate
python -m flask seed-dev-user --generate
# Optional – erster SuperAdmin (nur eine Zeile):
flask seed-dev-user --username admin --password Admin123 --superadmin
python -m flask seed-dev-user --username admin --password Admin123 --superadmin
```

**Windows (PowerShell):**  
*Erste Zeile = Kurzform, zweite Zeile = Python -m — pro Aktion nur eine ausführen.*

```powershell
cd Backend
pip install -r requirements.txt
python -m pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env
# .env bearbeiten: SECRET_KEY, JWT_SECRET_KEY (oder DEV_SECRETS_OK=1); FLASK_APP=run:app
flask init-db
python -m flask init-db
flask db upgrade
python -m flask db upgrade
# Falls "table already exists" nach init-db:
flask db stamp head
python -m flask db stamp head
# Optional (DEV_SECRETS_OK=1) – Dev-User:
flask seed-dev-user --generate
python -m flask seed-dev-user --generate
# Optional – erster SuperAdmin:
flask seed-dev-user --username admin --password Admin123 --superadmin
python -m flask seed-dev-user --username admin --password Admin123 --superadmin
```

**PyCharm (Linux oder Windows):**

- **Working Directory:** Immer `Backend` (Run Configuration oder im Terminal `cd Backend`).
- **Terminal (Alt+F12):** Eine der Zeilen pro Aktion ausführen (Kurzform oder Python -m):
  ```bash
  cd Backend
  python -m pip install -r requirements.txt
  python -m flask init-db
  python -m flask db upgrade
  python -m flask seed-dev-user --username admin --password Admin123 --superadmin
  ```
- **Run Configurations:** „Flask“ mit Target `init-db` / `run`; Working directory = `$ProjectFileDir$/Backend`; Environment aus `.env` (EnvFile-Plugin oder manuell).

---

## Start the server

**Linux (Bash / Terminal):** *Nur eine der drei Zeilen für „Server starten“ ausführen.*

```bash
cd Backend
export FLASK_APP=run:app
export FLASK_DEBUG=1
python run.py
flask run --port 5000
python -m flask run --port 5000
```

**Windows (PowerShell):** *Nur eine der drei Zeilen für „Server starten“ ausführen.*

```powershell
cd Backend
$env:FLASK_APP = "run:app"
$env:FLASK_DEBUG = "1"
python run.py
flask run --port 5000
python -m flask run --port 5000
```

**PyCharm (Linux oder Windows):**

- **Variante A – run.py:** Run Configuration „Python“: Script path = `Backend/run.py` (oder absoluter Pfad zu `run.py`), Working directory = `Backend`. Optional: Environment variables aus `.env` (EnvFile-Plugin oder manuell `FLASK_APP=run:app`, `FLASK_DEBUG=1`). Dann „Run“ (grüner Play).
- **Variante B – Flask CLI:** Run Configuration „Flask“: App = `run:app`, Optional: Target = leer lassen für `run`, dann Port 5000. Working directory = `Backend`. Oder Target = `run` und Additional options = `--port 5000`.
- **Terminal in PyCharm:** `cd Backend` dann `python run.py` oder `python -m flask run --port 5000` (mit `FLASK_APP=run:app` und `FLASK_DEBUG=1` in .env oder export).

Server: http://127.0.0.1:5000

---

## Further useful commands (Backend)

| Action | <span style="color:#0a0">**Kurzform**</span> | <span style="color:#00a">**Python -m**</span> |
|--------|-----------|-----------------------------|
| Dependencies installieren | `pip install -r requirements.txt` | `python -m pip install -r requirements.txt` |
| DB initialisieren (Tabellen + Stamp) | `flask init-db` | `python -m flask init-db` |
| Migrations anwenden | `flask db upgrade` | `python -m flask db upgrade` |
| Neue Migration erstellen | `flask db revision -m "description"` | `python -m flask db revision -m "description"` |
| Migrations-Status anzeigen | `flask db current` | `python -m flask db current` |
| Revision stempeln (ohne auszuführen) | `flask db stamp head` | `python -m flask db stamp head` |
| Dev-User (Moderator, role_level 0) | `flask seed-dev-user --username dev --password Pass1` | `python -m flask seed-dev-user --username dev --password Pass1` |
| Ersten SuperAdmin anlegen | `flask seed-dev-user --username admin --password Admin123 --superadmin` | `python -m flask seed-dev-user --username admin --password Admin123 --superadmin` |
| Admin-User (SuperAdmin) | `flask seed-admin-user --username admin --password Admin1` | `python -m flask seed-admin-user --username admin --password Admin1` |
| Bestehenden User auf role_level 100 setzen (z. B. Admin → SuperAdmin) | `flask set-user-role-level --username admin` | `python -m flask set-user-role-level --username admin` |
| Beispiel-News seeden | `flask seed-news` | `python -m flask seed-news` |
| Tests ausführen | `pytest tests` | `python -m pytest tests` |
| Tests ohne Coverage | `pytest tests --no-cov` | `python -m pytest tests --no-cov` |

**Hinweis:** Alle Befehle aus dem Backend-Verzeichnis ausführen (`cd Backend`). Unter PowerShell mehrere Befehle mit `;` trennen, z. B. `cd Backend; python -m flask db upgrade`.

---

## SuperAdmin / erster Admin

- **SuperAdmin** = Admin mit `role_level >= 100` (nur sprachliche Bezeichnung). Nur ein SuperAdmin darf das eigene `role_level` erhöhen; alle anderen Admins/Moderatoren haben `role_level` 0 (oder von einem SuperAdmin gesetzt).
- **Alle User starten mit `role_level` 0.** Einen SuperAdmin gibt es nur, wenn er per Seed angelegt wurde.
- **Ersten SuperAdmin anlegen** (nur mit `DEV_SECRETS_OK=1`):

  **Variante A – seed-dev-user mit `--superadmin` (empfohlen):**
  - <span style="color:#0a0">**Kurzform:**</span> `flask seed-dev-user --username admin --password Admin123 --superadmin`
  - <span style="color:#00a">**Python -m:**</span> `python -m flask seed-dev-user --username admin --password Admin123 --superadmin`

  **Variante B – seed-admin-user:**
  - <span style="color:#0a0">**Kurzform:**</span> `flask seed-admin-user --username admin --password Admin1`
  - <span style="color:#00a">**Python -m:**</span> `python -m flask seed-admin-user --username admin --password Admin1`

- Danach mit diesem User einloggen (Web oder API); der Admin kann dann z. B. `/manage/users` nutzen und anderen Usern Rollen zuweisen. Das Zuweisen einer Rolle ändert **nicht** den `role_level` des Users (der bleibt 0, außer ein SuperAdmin setzt ihn explizit).
- **Bestehenden Admin zu SuperAdmin machen:** `flask set-user-role-level --username <name>` bzw. `python -m flask set-user-role-level --username <name>` (setzt `role_level` auf 100). Optional: `--role-level 50` für anderen Wert.

---

## Web flow

1. Open http://127.0.0.1:5000/ in the browser.
2. "Log in" → enter username/password (e.g. from seed-dev-user).
3. After login you are redirected to /dashboard.
4. "Log out" (button in header) → POST to logout.

---

## Management frontend (editorial area)

The **Frontend** app exposes a protected management area for staff and admins:

- **URL:** `http://127.0.0.1:5001/manage` (or `/manage/login` to log in).
- **Auth:** Login form sends credentials to backend `POST /api/v1/auth/login`; the returned JWT is stored in **sessionStorage** (not localStorage). All management API calls use a central helper that sends `Authorization: Bearer <token>`. If the backend returns 401, the frontend clears the token and redirects to `/manage/login`. Current user is loaded via `GET /api/v1/auth/me` and shown in the header (username, role); logout clears the token.
- **Pages:** `/manage` (dashboard), `/manage/news` (news list/create/edit/publish/unpublish/delete), `/manage/users` (user table and edit; **admin only**), `/manage/wiki` (wiki markdown editor). Role-based visibility: the "Users" link is shown only to users with role `admin`.
- **Config:** Same as the public frontend: `BACKEND_API_URL` must point to the backend (e.g. `http://127.0.0.1:5000`). CORS must allow the frontend origin so the browser can call the API.

---

## API flow (example)

**Bash / Terminal:**

```bash
# 1. Register (or use existing user)
curl -X POST http://127.0.0.1:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"Alice123"}'

# 2. Login, get token from response
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"Alice123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. Call protected route
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/auth/me
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/test/protected
```

**PowerShell:**

```powershell
# 1. Register
curl.exe -X POST http://127.0.0.1:5000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"alice\",\"email\":\"alice@example.com\",\"password\":\"Alice123\"}'

# 2. Login, store token in variable
$response = curl.exe -s -X POST http://127.0.0.1:5000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"alice\",\"password\":\"Alice123\"}'
$TOKEN = ( $response | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])" )

# 3. Protected route
curl.exe -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/auth/me
curl.exe -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5000/api/v1/test/protected
```

---

## Wiki API (editorial)

- **GET /api/v1/wiki** — Returns wiki source and rendered HTML. Requires JWT with **moderator** or **admin** role. Response: `{ "content": "<markdown>", "html": "<html or null>" }`. File: `Backend/content/wiki.md`.
- **PUT /api/v1/wiki** — Updates wiki markdown. Requires JWT with moderator or admin. Body: `{ "content": "<markdown string>" }`. Activity is logged when the logging system is used.

---

## Health checks

- **Web:** `GET /health` → JSON `{"status":"ok"}` (unauthenticated).
- **API:** `GET /api/v1/health` → JSON `{"status":"ok"}` (unauthenticated).

---

## Errors & limits

- **Web routes** (e.g. `/`, `/login`, `/dashboard`): 404/500 as HTML (templates).
- **API routes** (under `/api/`): 404, 429, 500 and JWT 401 as JSON `{"error": "..."}`.
- **Rate limit:** 429 as JSON; default from `RATELIMIT_DEFAULT`.

---

## Troubleshooting

- **SECRET_KEY must be set:** In `.env` set `SECRET_KEY` and `JWT_SECRET_KEY`, or for local dev set `DEV_SECRETS_OK=1`.
- **CSRF invalid on login:** Login form must include CSRF token (already present in templates).
- **CORS / "Network error" vom Frontend:** Am Backend (z. B. in den Environment-Variablen der Web-App oder in `.env`) `CORS_ORIGINS` auf die exakte Frontend-Origin setzen. Keine Leerzeichen um Kommas, keine trailing slashes. Beispiele: Frontend lokal → `CORS_ORIGINS=http://127.0.0.1:5001,http://localhost:5001`; Frontend auf PythonAnywhere-Subdomain → `CORS_ORIGINS=https://deine-frontend-app.pythonanywhere.com`. Danach Backend-Web-App neu laden. Siehe `.env.example` (CORS-Abschnitt).
- **PowerShell: "&&" unknown:** On PowerShell separate commands with `;` (e.g. `cd Backend; python -m flask db upgrade`) or use one command per line.
- **flask: command not found:** Immer die <span style="color:#00a">**Python -m**</span>-Zeile verwenden (Tabelle „Further useful commands“); aus dem Backend-Verzeichnis ausführen.
- **401 Unauthorized on API:** Two cases: (1) **Login** (`POST /auth/login`) returns 401 → wrong username or password. (2) **Other API calls** (e.g. `GET /api/v1/users`) return 401 → missing or invalid JWT: first call `POST /auth/login` with JSON `{"username":"...","password":"..."}`, then send the returned `access_token` in the header `Authorization: Bearer <access_token>`. Note: `seed-dev-user` creates a **moderator** user; for admin-only endpoints use `seed-admin-user`, e.g. `python -m flask seed-admin-user --username admin --password Admin1` (with `DEV_SECRETS_OK=1`).
