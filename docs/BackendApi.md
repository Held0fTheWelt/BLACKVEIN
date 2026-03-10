# Backend API – Funktionsbeschreibung

Die Backend-API wird unter dem Präfix **`/api/v1`** bereitgestellt. Alle Antworten sind JSON. Geschützte Endpoints erwarten den Header **`Authorization: Bearer <JWT>`**.

---

## Übersicht

| Bereich   | Endpoints                                                                 |
|----------|---------------------------------------------------------------------------|
| **Auth** | Register, Login, Me                                                       |
| **System** | Health, Test Protected                                                   |
| **Users** | List (GET, Admin), Get (GET), Update (PUT), Delete (DELETE, Admin)       |
| **News** | List (GET), Detail (GET), Create (POST), Update (PUT), Delete, Publish, Unpublish |

---

## 1. Auth

### 1.1 Register – Benutzer anlegen

**`POST /api/v1/auth/register`**

Legt einen neuen Benutzer an. E-Mail ist Pflicht. Nach der Registrierung wird ein E-Mail-Verifikations-Token erzeugt und eine Verifikations-E-Mail gesendet (oder in Dev ohne `MAIL_ENABLED` nur geloggt). Der User kann sich erst nach Klick auf den Aktivierungs-Link einloggen.

- **Rate Limit:** 10 pro Minute  
- **Auth:** Keine  

**Request-Body (JSON):**

| Feld      | Typ    | Pflicht | Beschreibung                          |
|-----------|--------|--------|----------------------------------------|
| `username` | string | ja     | Eindeutig, 2–80 Zeichen, `a-zA-Z0-9_-` |
| `email`    | string | ja     | Eindeutig, gültiges Format             |
| `password` | string | ja     | Mind. 8 Zeichen, Groß-/Kleinbuchstabe, Ziffer |

**Response:**

- **201 Created:** `{ "id": <number>, "username": "<string>" }`
- **400 Bad Request:** `{ "error": "<Fehlermeldung>" }` (z. B. ungültiges Passwort, fehlende Felder)
- **409 Conflict:** `{ "error": "Username already taken" }` oder `"Email already registered"`

---

### 1.2 Login – JWT abrufen

**`POST /api/v1/auth/login`**

Authentifiziert mit Benutzername und Passwort und gibt ein JWT sowie die User-Daten zurück. Nur möglich, wenn die E-Mail des Users verifiziert ist (siehe 0.0.7).

- **Rate Limit:** 20 pro Minute  
- **Auth:** Keine  

**Request-Body (JSON):**

| Feld       | Typ    | Pflicht | Beschreibung |
|------------|--------|--------|---------------|
| `username` | string | ja     | Benutzername  |
| `password` | string | ja     | Passwort      |

**Response:**

- **200 OK:**  
  `{ "access_token": "<JWT>", "user": { "id": <number>, "username": "<string>", "role": "<string>" } }`
- **400 Bad Request:** `{ "error": "Invalid or missing JSON body" }` oder `"Username and password are required"`
- **401 Unauthorized:** `{ "error": "Invalid username or password" }`
- **403 Forbidden:** `{ "error": "Email not verified." }` – E-Mail noch nicht bestätigt

---

### 1.3 Me – aktueller Benutzer

**`GET /api/v1/auth/me`**

Gibt den aus dem JWT ermittelten Benutzer zurück.

- **Rate Limit:** 60 pro Minute  
- **Auth:** Bearer JWT (erforderlich)  

**Response:**

- **200 OK:** `{ "id": <number>, "username": "<string>", "role": "<string>" }`  
  Mögliche Rollen: `user`, `editor`, `admin`.
- **401 Unauthorized:** Fehlender oder ungültiger Token: `{ "error": "Authorization required. Missing or invalid token." }` bzw. `"Invalid or expired token."`
- **404 Not Found:** `{ "error": "User not found" }` (Token gültig, User in DB nicht mehr vorhanden)

---

## 2. System

### 2.1 Health – API-Status

**`GET /api/v1/health`**

Einfacher API-Health-Check.

- **Rate Limit:** 100 pro Minute  
- **Auth:** Keine  

**Response:**

- **200 OK:** `{ "status": "ok" }`

---

### 2.2 Test Protected – geschützte Route (Beispiel)

**`GET /api/v1/test/protected`**

Beispiel für eine geschützte Route. Nur mit gültigem JWT aufrufbar.

- **Rate Limit:** 60 pro Minute  
- **Auth:** Bearer JWT (erforderlich)  

**Response:**

- **200 OK:**  
  `{ "message": "ok", "user_id": <number>, "username": "<string>" }`
- **401:** Wie bei Me (fehlender/ungültiger Token)

---

## 3. News

Öffentliche Lese-Endpoints (Liste, Detail) sind ohne Auth. Schreib- und Status-Änderungen (Create, Update, Delete, Publish, Unpublish) erfordern JWT und die Rolle **editor** oder **admin**; sonst 401 (kein Token) oder 403 (Forbidden).

---

### 3.1 News List – veröffentlichte Artikel auflisten

**`GET /api/v1/news`**

Liefert eine paginierte Liste **nur veröffentlichter** Artikel. Unveröffentlichte bzw. für die Zukunft geplante Artikel erscheinen nicht.

- **Rate Limit:** 60 pro Minute  
- **Auth:** Keine  

**Query-Parameter:**

| Parameter   | Typ    | Default        | Beschreibung                                      |
|------------|--------|----------------|---------------------------------------------------|
| `q`        | string | –              | Suchbegriff (Suche in Titel/Inhalt)               |
| `sort`     | string | `published_at` | Sortierung: `published_at`, `created_at`, `updated_at`, `title` |
| `direction`| string | `desc`         | `asc` oder `desc`                                 |
| `page`     | int    | 1              | Seitennummer (≥ 1)                                |
| `limit`    | int    | 20             | Einträge pro Seite (1–100)                        |
| `category` | string | –              | Filter nach Kategorie                             |

**Response:**

- **200 OK:**  
  `{ "items": [ <News-Objekt>, ... ], "total": <number>, "page": <number>, "per_page": <number> }`

**News-Objekt (Auszug):**  
`id`, `title`, `slug`, `summary`, `content`, `author_id`, `author_name`, `is_published`, `published_at` (ISO-8601), `created_at`, `updated_at`, `cover_image`, `category`

---

### 3.2 News Detail – einzelnen Artikel abrufen

**`GET /api/v1/news/<id>`**

Liefert einen veröffentlichten Artikel anhand der numerischen ID. Unveröffentlichte oder zukünftig geplante Artikel liefern 404.

- **Rate Limit:** 60 pro Minute  
- **Auth:** Keine  

**Response:**

- **200 OK:** Ein einzelnes News-Objekt (gleiche Felder wie in der Liste).
- **404 Not Found:** `{ "error": "Not found" }`

---

### 3.3 News Create – Artikel anlegen

**`POST /api/v1/news`**

Erstellt einen neuen News-Artikel. Autor wird aus der JWT-Identity übernommen.

- **Rate Limit:** 30 pro Minute  
- **Auth:** Bearer JWT, Rolle **editor** oder **admin**  

**Request-Body (JSON):**

| Feld          | Typ    | Pflicht | Beschreibung                |
|---------------|--------|--------|-----------------------------|
| `title`       | string | ja     | Titel                       |
| `slug`        | string | ja     | Eindeutiger URL-Slug        |
| `content`     | string | ja     | Inhalt (Text)               |
| `summary`     | string | nein   | Kurzfassung                 |
| `is_published`| bool   | nein   | Default: false              |
| `cover_image` | string | nein   | URL oder Pfad               |
| `category`    | string | nein   | Kategorie                   |

**Response:**

- **201 Created:** Das erstellte News-Objekt.
- **400 Bad Request:** `{ "error": "title, slug, and content are required" }` oder andere Validierungsfehler.
- **401/403:** Kein Token oder Rolle nicht editor/admin.
- **409 Conflict:** `{ "error": "Slug already in use" }`

---

### 3.4 News Update – Artikel bearbeiten

**`PUT /api/v1/news/<id>`**

Aktualisiert einen bestehenden Artikel. Nur angegebene Felder werden geändert.

- **Rate Limit:** 30 pro Minute  
- **Auth:** Bearer JWT, Rolle **editor** oder **admin**  

**Request-Body (JSON):** Alle Felder optional: `title`, `slug`, `summary`, `content`, `cover_image`, `category`.

**Response:**

- **200 OK:** Das aktualisierte News-Objekt.
- **400/401/403:** Wie bei Create.
- **404 Not Found:** `{ "error": "News not found" }`
- **409 Conflict:** `{ "error": "Slug already in use" }`

---

### 3.5 News Delete – Artikel löschen

**`DELETE /api/v1/news/<id>`**

Löscht einen Artikel.

- **Rate Limit:** 30 pro Minute  
- **Auth:** Bearer JWT, Rolle **editor** oder **admin**  

**Response:**

- **200 OK:** `{ "message": "Deleted" }`
- **404 Not Found:** `{ "error": "<Fehlermeldung>" }`
- **401/403:** Wie oben.

---

### 3.6 News Publish – Artikel veröffentlichen

**`POST /api/v1/news/<id>/publish`**

Setzt den Artikel auf „veröffentlicht“ (und `published_at` auf jetzt).

- **Rate Limit:** 30 pro Minute  
- **Auth:** Bearer JWT, Rolle **editor** oder **admin**  

**Response:**

- **200 OK:** Das aktualisierte News-Objekt (mit `is_published: true`, `published_at` gesetzt).
- **404:** Artikel nicht gefunden.
- **401/403:** Wie oben.

---

### 3.7 News Unpublish – Veröffentlichung aufheben

**`POST /api/v1/news/<id>/unpublish`**

Setzt den Artikel auf „nicht veröffentlicht“ (`is_published: false`, `published_at` optional zurückgesetzt).

- **Rate Limit:** 30 pro Minute  
- **Auth:** Bearer JWT, Rolle **editor** oder **admin**  

**Response:**

- **200 OK:** Das aktualisierte News-Objekt.
- **404/401/403:** Wie bei Publish.

---

## 4. Users (CRUD)

Alle User-Endpoints erfordern **Bearer JWT**. **List** und **Delete** nur für Rolle **admin**; **Get** und **Update** für Admin (beliebiger User) oder für den eigenen User (Self).

### 4.1 Users List – Benutzer auflisten (Admin)

**`GET /api/v1/users`**

Paginierte Liste aller User. Nur **admin**.

- **Rate Limit:** 60 pro Minute  
- **Auth:** Bearer JWT, Rolle **admin**  

**Query-Parameter:**

| Parameter | Typ    | Default | Beschreibung                    |
|-----------|--------|--------|----------------------------------|
| `page`    | int    | 1      | Seitennummer (≥ 1)              |
| `limit`   | int    | 20     | Einträge pro Seite (1–100)      |
| `q`       | string | –      | Suche in Benutzername/E-Mail    |

**Response:**

- **200 OK:** `{ "items": [ { "id", "username", "role", "email" }, ... ], "total", "page", "per_page" }`
- **403:** Kein Admin

---

### 4.2 Users Get – einen User abrufen

**`GET /api/v1/users/<id>`**

Einzelner User: **Admin** darf jeden abrufen, sonst nur das **eigene** Profil (`id` = JWT-User). Bei eigener Abfrage und bei Admin enthält die Antwort `email`.

- **Rate Limit:** 60 pro Minute  
- **Auth:** Bearer JWT (Admin oder Self)  

**Response:**

- **200 OK:** `{ "id", "username", "role" }` oder inkl. `"email"` (siehe oben)
- **403:** Fremder User, kein Admin
- **404:** User nicht gefunden

---

### 4.3 Users Update – User bearbeiten

**`PUT /api/v1/users/<id>`**

User aktualisieren: **Admin** darf jeden und kann `role` setzen; sonst nur **eigenes** Profil (ohne `role`). Body: alle Felder optional.

- **Rate Limit:** 30 pro Minute  
- **Auth:** Bearer JWT (Admin oder Self)  

**Request-Body (JSON):**

| Feld               | Typ    | Beschreibung                                              |
|--------------------|--------|-----------------------------------------------------------|
| `username`         | string | Neuer Benutzername (eindeutig, 2–80 Zeichen, `a-zA-Z0-9_-`) |
| `email`            | string | Neue E-Mail (eindeutig, gültiges Format)                  |
| `password`         | string | Neues Passwort (Regeln wie bei Registrierung)            |
| `current_password` | string | Beim Ändern des **eigenen** Passworts erforderlich       |
| `role`             | string | Nur **Admin:** `user`, `editor`, `admin`                 |

**Response:**

- **200 OK:** Aktualisiertes User-Objekt (wie bei Get, inkl. `email` wenn Admin/Self)
- **400:** Validierungsfehler, z. B. „Current password is incorrect“
- **403:** Kein Recht für diesen User
- **404:** User nicht gefunden
- **409:** „Username already taken“ oder „Email already registered“

---

### 4.4 Users Delete – User löschen (Admin)

**`DELETE /api/v1/users/<id>`**

User endgültig löschen. Nur **admin**. News-Einträge des Users bleiben erhalten, `author_id` wird auf `null` gesetzt.

- **Rate Limit:** 30 pro Minute  
- **Auth:** Bearer JWT, Rolle **admin**  

**Response:**

- **200 OK:** `{ "message": "Deleted" }`
- **403:** Kein Admin
- **404:** User nicht gefunden

---

## 5. Allgemeines

### 5.1 Authentifizierung

- Geschützte Endpoints erwarten den Header: **`Authorization: Bearer <access_token>`**  
  Das Token erhält man von **`POST /api/v1/auth/login`**.
- Ungültiger oder abgelaufener Token: **401** mit JSON-`error`.
- Gültiger Token, aber unzureichende Rechte (z. B. Rolle `user` bei News-Schreibzugriff): **403 Forbidden**.

### 5.2 Fehlerantworten

- API-Fehler sind JSON: `{ "error": "<Meldung>" }`.
- Bei fehlendem oder ungültigem JSON-Body: **400** mit entsprechender `error`-Meldung.

### 5.3 CORS

- Wenn Frontend und Backend unterschiedliche Origins nutzen, muss **CORS_ORIGINS** im Backend gesetzt werden (z. B. `http://localhost:5001,http://127.0.0.1:5001`), damit der Browser API-Aufrufe erlaubt.

### 5.4 Rate Limits

- Pro Endpoint gelten die oben genannten Limits (z. B. 10/min Register, 20/min Login, 60/min Health/News List). Überschreitung führt in der Regel zu **429 Too Many Requests** (konfigurationsabhängig).
