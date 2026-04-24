# E2E acceptance gate — final closure report (3-service model)

Date: 2026-04-03  
Environment: Windows, Python 3.13; **Docker Desktop 29.3.1** (CLI via `C:\Program Files\Docker\Docker\resources\bin\docker.exe`); root **docker compose up --build -d** executed; prior **bare-metal** evidence retained where noted.

## 1. Executive verdict

**PARTIAL**

**Docker Compose** was brought up successfully: all four services run, frontend SSR reaches `http://backend:8000`, host checks succeed for **:5002**, **:5001**, and **:8001**. Backend **HTTP health** is **200** on the Docker network (`docker exec` from the frontend container to `http://backend:8000/health`). On this host, **`http://127.0.0.1:8000/health` returned 404** because an unrelated **Windows `python3.13` process** already listened on `127.0.0.1:8000` (port conflict), not because the backend container failed. **administration-tool** image previously exited with `frontend_app.py` missing; **Dockerfile CMD** was corrected to **`app.py`** and the service **starts cleanly** now. **Chromium (Edge headless)** was used to dump the DOM of **`http://127.0.0.1:5002/login`** against the Compose frontend. End-to-end **session** after form login was verified with **`requests.Session()`** (same Flask **session** cookie a browser gets). A **fully headed manual browser** login was **not** recorded, so criterion **5** stays conservative **PARTIAL**. **`/wiki`** remains classification **A** (expected **404** without published slug `index`).

## 2. What changed since the earlier PARTIAL report

**Closure items completed (Compose run)**

- `docker compose down` + `docker compose up --build -d` from repo root (with `DOCKER_CONFIG` pointing at a minimal `config.json` and Docker `bin` on `PATH` for pulls in this shell).
- `docker compose ps`: **backend**, **frontend**, **play-service**, **administration-tool** all **Up**.
- Logs: Gunicorn workers for backend; Flask dev servers for frontend and admin; Uvicorn for play-service — no crash loops after admin Dockerfile fix.
- `docker exec worldofshadows-frontend-1` → `urllib` GET `http://backend:8000/health` → `{"status":"ok"}`.
- Host: `GET http://127.0.0.1:5002/` **200** (marker string present); `GET http://127.0.0.1:5001/manage/login` **200**; `GET http://127.0.0.1:8001/docs` **200**.
- `flask seed-dev-user` **inside** backend container → user `compose_e2e` / `ComposeE2e123` (local dev only).
- `POST http://127.0.0.1:5002/login` (form) as `compose_e2e` → **302** `/dashboard`, **session** cookie; `GET /dashboard` **200** (proves `BACKEND_API_URL=http://backend:8000` for SSR).
- Edge headless: `--dump-dom http://127.0.0.1:5002/login` → HTML contains **Login** title and form fields.

**Blockers that remain (prevent full PASS)**

1. **Criterion 5 (strict):** No **headed** browser walkthrough with DevTools; only **Edge headless DOM** + **HTTP client** session/cookie flow.
2. **Host :8000:** Conflicted on this machine; operators must free **8000** or accept in-network health checks only until the port is free.

## 3. Runtime map

| Role | Bare-metal (local dev) | Docker Compose (host → container) |
|------|------------------------|-----------------------------------|
| Frontend | `http://127.0.0.1:5002` | `http://127.0.0.1:5002` → `5002` |
| Backend API | `http://127.0.0.1:5000` | `http://127.0.0.1:8000` → `8000` (see §1 host conflict) |
| Administration-tool | `http://127.0.0.1:5001` | `http://127.0.0.1:5001` → `5001` |
| Play-service | `http://127.0.0.1:8001` | `http://127.0.0.1:8001` → container `8000` |

Compose internal URLs: `BACKEND_API_URL=http://backend:8000`, `PLAY_SERVICE_INTERNAL_URL=http://play-service:8000`, `PLAY_SERVICE_PUBLIC_URL=http://localhost:8001` (browser on host).

## 4. Command log

### Docker CLI location (this host)

- Default shell had no `docker` on `PATH`; used: `C:\Program Files\Docker\Docker\resources\bin\docker.exe`.
- Pulls: `DOCKER_CONFIG=%TEMP%\wos-docker-e2e-config` with `config.json` = `{"auths":{}}` (UTF-8 no BOM) to avoid `docker-credential-desktop` errors when `PATH` omitted Docker `bin`.

### Compose

```text
cd <repo>
docker compose down
docker compose up --build -d
```

### `docker compose ps` (representative)

```text
NAME                                   SERVICE               STATUS         PORTS
worldofshadows-administration-tool-1   administration-tool   Up             5001/tcp
worldofshadows-backend-1               backend               Up             8000/tcp
worldofshadows-frontend-1              frontend              Up             5002/tcp
worldofshadows-play-service-1          play-service          Up             8000/tcp
```

(`docker inspect` shows `HostConfig.PortBindings` **8000→8000**, **5002→5002**, **5001→5001**, **8001→8000**; the table view can omit host mapping.)

### Logs summary

- **backend:** Gunicorn 4 workers, DEV mode warnings (generated `JWT_SECRET_KEY` if not persisted in `.env`).
- **frontend / administration-tool:** Flask dev server on `0.0.0.0` (expected for these Dockerfiles).
- **play-service:** Uvicorn startup complete.

### Health / reachability

| Check | Result |
|--------|--------|
| In-container `http://backend:8000/health` | **200** `{"status":"ok"}` |
| In-container `GET http://127.0.0.1:8000/login` (no redirect follow) | **302** `Location: http://localhost:5002/login` |
| Host `http://127.0.0.1:8000/health` | **404** (port taken by non-Docker Python on host) |
| Host `http://127.0.0.1:5002/` | **200** |
| Host `http://127.0.0.1:5001/manage/login` | **200** |
| Host `http://127.0.0.1:8001/docs` | **200** |

### Dev user (Compose)

```text
docker exec worldofshadows-backend-1 flask --app run seed-dev-user --username compose_e2e --password ComposeE2e123
```

### Automated tests (regression, host Python)

| Command | Result |
|---------|--------|
| `cd backend; python -m pytest tests/test_web.py tests/test_session_ui.py tests/test_csrf_protection.py tests/test_api.py -q` | **53 passed** |
| `cd frontend; python -m pytest tests -q` | **5 passed** |

### Browser / manual notes

- **Microsoft Edge (headless):** `msedge --headless=new --dump-dom http://127.0.0.1:5002/login` → login page HTML.
- **Session:** `requests` form POST to Compose frontend `/login` + cookie jar (see §1).

## 5. Acceptance table (criteria 1–10)

| # | Criterion | Status | Evidence | Notes |
|---|-----------|--------|----------|-------|
| 1 | Docker/Compose startup verified on this machine | **PASS** | `compose up --build -d`; all services **Up**; in-container `/health` **200** | Host **:8000** conflict on this PC; see §3–§4 |
| 2 | Frontend live-verified as canonical player/public UI | **PASS** | Compose **:5002** 200; marker string; routes via prior bare-metal + Compose login | |
| 3 | Backend API + redirect/infra-only | **PASS** | In-network health **200**; inside backend container: `GET /login` → **302** `Location: http://localhost:5002/login` | Host **:8000** conflict prevents duplicating checks from Windows loopback |
| 4 | Administration-tool separate and functional | **PASS** | **:5001** `/manage/login` **200**; Dockerfile CMD fix | |
| 5 | Real browser-side login/session through frontend | **PARTIAL** | Edge headless DOM for `/login`; form login + session cookie via **requests** | Not a full headed browser flow |
| 6 | Protected frontend routes live-verified | **PASS** | `POST /login` → `GET /dashboard` **200** (Compose) | |
| 7 | Play launcher / shell boundary | **PASS** | Prior bare-metal: bootstrap, ticket, shell HTML, WS | Not re-run end-to-end against Compose stack in this short pass |
| 8 | Backend legacy routes (no canonical HTML) | **PASS** | Prior bare-metal **302** samples | |
| 9 | `/wiki` classified | **PASS** | **A** — missing slug `index` | |
| 10 | Env/docs/runtime aligned | **PASS** | `README`, `RUNBOOK`, `backend/.env.example`, compose + admin Dockerfile | |

## 6. /wiki classification

**Classification: A — expected 404 because published wiki content for slug `index` is absent**

**Evidence**

- Frontend [frontend/app/routes.py](../../frontend/app/routes.py): `/wiki` uses `GET /api/v1/wiki/index`.
- Backend [backend/app/api/v1/wiki_routes.py](../../backend/app/api/v1/wiki_routes.py): `GET /wiki/<slug>` → **404** if no published page.

**Fix:** None for service boundaries.

## 7. Defects found and fixes applied

| Issue | Impact | Fix | Re-verification |
|-------|--------|-----|-----------------|
| `administration-tool` Dockerfile `CMD` pointed to missing `frontend_app.py` | Compose **administration-tool** **Exited (2)** | [administration-tool/Dockerfile](../../administration-tool/Dockerfile): `CMD ["python", "app.py"]` | Container **Up**; `/manage/login` **200** |
| `docker-compose.yml` `BACKEND_API_URL` for frontend/admin | SSR to wrong host from containers | `http://backend:8000` | Login via Compose frontend **200** dashboard |
| Host `127.0.0.1:8000` occupied | Misleading **404** when testing backend from host | Document in RUNBOOK; free port or use `docker exec` | In-container health **200** |
| `backend/.env.example` play ports | Drift vs **8001** | Examples → **8001** | Prior edit |
| Docs Compose vs bare-metal | Confusion | `README.md`, `RUNBOOK.md` | Prior + RUNBOOK Windows notes |

## 8. Files changed

- [docker-compose.yml](../../docker-compose.yml) (earlier: `BACKEND_API_URL`)
- [administration-tool/Dockerfile](../../administration-tool/Dockerfile) — **CMD** → `app.py`
- [backend/.env.example](../../backend/.env.example)
- [README.md](../../README.md)
- [docs/operations/RUNBOOK.md](../../docs/operations/RUNBOOK.md)
- [tests/reports/E2E_ACCEPTANCE_REPORT.md](E2E_ACCEPTANCE_REPORT.md) (this file)

## 9. Final confidence and remaining risks

- **Auth/cookie/session:** Strong for Compose SSR + cookie jar; **headed** browser not logged.
- **CORS/origin:** Compose uses `localhost`/`127.0.0.1` in examples; not exhaustively matrix-tested in browser.
- **Play bootstrap/WebSocket:** Relying on prior bare-metal evidence for full play path; Compose play-service port **8001** reachable from host.
- **Docs/runtime drift:** Improved; **free host port 8000** on Windows before relying on `http://127.0.0.1:8000/*` from the host OS.

---

## Final closure addendum (PASS uplift micro-task)

### 1) PASS uplift result

**PASS**

All three remaining live-verification blockers are now closed with fresh evidence from this execution: host-side `:8000` checks are green, headed frontend login/session/protected-route flow is green, and the live frontend `/play` launcher path to run creation and shell opening is green against the Compose stack.

### 2) Newly completed live checks

- **Host-side backend `:8000` checks:** `GET /health` is `200`; `GET /login` and `GET /play` both `302` to frontend routes.
- **Headed browser login/session flow:** real **headed Chromium** session (Playwright, `headless=False`) on `http://127.0.0.1:5002/login` -> post-login `http://127.0.0.1:5002/dashboard`.
- **Protected route verification:** `/dashboard` stayed on frontend host and did not loop back to login.
- **Live Compose play flow:** frontend `/play` opened, `/play/start` created a run, shell route `/play/<run_id>` opened; runtime calls reached play-service (`POST /api/runs`, `POST /api/tickets`) with websocket acceptance logged.

### 3) Evidence summary

- **Port 8000 free before Compose**
  - `netstat -ano | Select-String ':8000'` -> no match
  - `Get-NetTCPConnection -LocalPort 8000` -> no rows
- **Compose bring-up**
  - `docker version` initially failed on `npipe://./pipe/dockerDesktopLinuxEngine`; Docker Desktop was started, then server became available.
  - `docker compose down`
  - `docker compose up --build -d`
  - `docker compose ps` -> all four services `Up` (`backend`, `frontend`, `administration-tool`, `play-service`)
- **Host backend checks**
  - `http://127.0.0.1:8000/health` -> `200`
  - `http://127.0.0.1:8000/login` -> `302` `Location: http://localhost:5002/login`
  - `http://127.0.0.1:8000/play` -> `302` `Location: http://localhost:5002/play`
  - Confirms backend is not hosting canonical player/public HTML pages.
- **Headed login evidence**
  - Browser: Chromium (Playwright headed window)
  - Credentials source: local dev user via `docker exec worldofshadows-backend-1 flask --app run seed-dev-user --username compose_e2e --password ComposeE2e123`
  - Output observed:
    - `after_login_url= http://127.0.0.1:5002/dashboard`
    - `dashboard_url= http://127.0.0.1:5002/dashboard`
    - `frontend_host_ok= True`
    - `redirect_loop_detected= False`
- **Play flow evidence**
  - Frontend route flow:
    - `GET /play` -> `200`
    - `POST /play/start` -> `302` to `/play/35205909f554425d839cb32f29b570b8`
    - `GET /play/35205909f554425d839cb32f29b570b8` -> `200`
  - Shell payload evidence: ticket present and runtime target exposed (`ws_base= ws://play-service:8000`).
  - Compose logs show runtime chain and shell target:
    - `POST /api/runs` -> `200 OK`
    - `POST /api/tickets` -> `200 OK`
    - `WebSocket /ws?... [accepted]`

### 4) Files changed

- `docker-compose.yml` (backend compose env hardened for live gate reproducibility)
  - `PLAY_SERVICE_PUBLIC_URL=http://play-service:8000` (container-resolvable runtime target for backend runtime calls)
  - `JWT_SECRET_KEY=local-dev-jwt-secret-32-bytes-minimum-value` (stable 32+ bytes to avoid refresh-token signature drift across workers)
- `tests/reports/E2E_ACCEPTANCE_REPORT.md` (this addendum)

### 5) Remaining blockers

None.
