# M0 Gate Checklist (Einziger verbleibender „M0-Task“)

Ziel: Nach Placement dieser Dokumente muss M0 nur noch **geprüft** werden.

## 1) Entscheidungen bestätigen
- [ ] Host für Phase A ist lokal (Operator), MCP Transport = stdio
- [ ] MCP spricht Backend remote über HTTPS (PythonAnywhere Default)
- [ ] Phase A bleibt read-only/preview-only (keine write tools)

## 2) Repo Evidence verifizieren
- [ ] `backend/app/api/__init__.py` registriert Blueprint `/api/v1`
- [ ] `backend/app/api/v1/session_routes.py` enthält:
  - [ ] POST `/sessions`
  - [ ] GET `/sessions/<id>`
  - [ ] POST `/sessions/<id>/turns`
  - [ ] GET `/sessions/<id>/logs`
  - [ ] GET `/sessions/<id>/state`
- [ ] `backend/app/web/routes.py` enthält `GET /health`
- [ ] Content Module vorhanden: `content/modules/god_of_carnage/`

## 3) Security Baseline prüfen
- [ ] Ist es akzeptabel, dass Session API ggf. (noch) nicht auth-geschützt ist?
- [ ] Falls nein: Service Token/AuthZ als A1.3 Ergänzung einplanen (GAP-3).

## 4) Tool Inventory v0 freigeben
- [ ] P0 Tools in `05_M0_tool_inventory_v0.md` sind korrekt und ausreichend.
- [ ] P1 Tools (local FS Content Reads) sind im Operator-Setup praktikabel.

## Exit Criteria (M0 abgeschlossen)
- Alle Häkchen gesetzt ODER Abweichungen dokumentiert + Entscheidung getroffen.
- A1 kann ohne weitere Architekturfragen implementiert werden.

