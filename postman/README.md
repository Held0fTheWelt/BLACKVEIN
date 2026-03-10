# Postman – World of Shadows API

## Dateien

- **WorldOfShadows_API.postman_collection.json** – Collection mit allen API-Requests und **Test-Skripten** (Status-Codes und Response-Assertions).
- **WorldOfShadows_Local.postman_environment.json** – Lokale Test-Umgebung (localhost:5000, Admin-Credentials).
- **WorldOfShadows_Test.postman_environment.json** – Zusätzliche Test-Umgebung (z. B. für testuser / andere Base-URL).

## Einrichtung

1. In Postman: **Import** → Collection und beide Environment-Dateien importieren.
2. Oben rechts **Environment** wählen (z. B. „World of Shadows – Local“).
3. Backend starten: `cd Backend && flask run` (oder `python run.py`), Standard-Port 5000.

## Umgebungsvariablen (Full Test Environment)

| Variable | Beschreibung | Beispiel |
|----------|--------------|----------|
| `baseUrl` | Backend-Basis-URL | `http://localhost:5000` |
| `apiPath` | API-Prefix (optional) | `/api/v1` |
| `username` | Login-Benutzername | `admin` |
| `password` | Login-Passwort | (geheim) |
| `email` | E-Mail des Users | `admin@example.com` |
| `access_token` | JWT (wird von „Login“ gesetzt) | – |
| `user_id` | Aktuelle User-ID (von Login/Me/Register) | – |
| `target_user_id` | User-ID für Users Delete (von „Users List“ gesetzt, anderer User) | – |
| `news_id` | Eine News-ID (von „News List“ gesetzt) | – |
| `register_username` | Benutzername für Registrierung | `postman_user` |
| `register_email` | E-Mail für Registrierung | `postman@example.com` |
| `register_password` | Passwort für Registrierung | (geheim) |

## Ablauf

1. **Login (saves token)** ausführen → `access_token` und `user_id` werden gesetzt.
2. Geschützte Requests (Me, Test Protected, **Users**, News Write) nutzen automatisch **Authorization: Bearer {{access_token}}**.
3. **Users List** (nur Admin): setzt `target_user_id` auf einen anderen User für **Users Delete**.
4. **News List** setzt bei vorhandenen Einträgen `news_id` für **News Detail**.

## Collection Runner

- **Collection** auswählen → **Run**.
- Environment auswählen → **Run World of Shadows API**.
- Alle Requests werden nacheinander ausgeführt; bei jedem laufen die **Test-Skripte** (grün/rot).

Hinweis: **Users List** und **Users Delete** erfordern einen User mit Rolle **admin** (in der DB `role='admin'`). „Register“ erzeugt einen neuen User; bei wiederholtem Lauf 409 (Username/Email bereits vergeben), sofern `register_username`/`register_email` nicht geändert werden. Für einen sauberen Lauf zuerst nur **Login** und **System/News/Users** ausführen oder einmalig einen neuen Registrierungs-User verwenden.
