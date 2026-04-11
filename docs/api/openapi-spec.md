# OpenAPI-Spezifikation (Backend)

Das Backend listet alle HTTP-Endpunkte unter `/api/v1` maschinenlesbar in einer **OpenAPI-3.0.3**-Datei:

- **Repository:** [`openapi.yaml`](openapi.yaml) (Quelle; wird aus Flask-Routen synchronisiert)
- **Flask-Backend:** `GET /backend/openapi.yaml` (lokal oft `http://127.0.0.1:5000`; Root-`docker-compose` mappt den Backend-Container oft nach **`http://localhost:8000`**).
- **MkDocs** (`python -m mkdocs serve`, häufig ebenfalls Port 8000): statische Kopie unter **`/backend/openapi.yaml`** ([`docs/backend/openapi.yaml`](../backend/openapi.yaml), wird vom Generator mit ausgegeben) sowie **`/api/openapi.yaml`**. *Hinweis:* Laufen MkDocs und Docker-Backend beide auf 8000, einen Dienst auf einen anderen Port legen (z. B. `mkdocs serve -a 127.0.0.1:8001`).
- **Interaktive Ansicht (nur Flask):** `/backend/api-explorer` — Redoc auf dem Backend-Host (nicht MkDocs).

## Pflege

Wenn sich Routen unter `backend/app/api/v1/` ändern:

```bash
cd backend
python scripts/generate_openapi_spec.py --write
```

CI prüft mit `python scripts/generate_openapi_spec.py --check`, dass die Spec zum Code passt.

## Taxonomie

Tag-Namen, Zuordnung zu Domänen und zu den `/backend/*`-Infoseiten: [openapi-taxonomy.md](openapi-taxonomy.md).

## World Engine

Die **Play-Service-API** (`world-engine/`, FastAPI) ist **nicht** in `openapi.yaml` enthalten. Siehe [API README — World Engine](README.md#world-engine-api).
