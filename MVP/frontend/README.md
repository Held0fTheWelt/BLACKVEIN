# Frontend Service (Player/Public)

This service is the canonical player/public web frontend.

It owns:
- login/register/logout UI
- dashboard/news/wiki/community pages
- game menu and play shell browser routes
- browser-side integration with backend API and play-service bootstrap

It does **not** include admin/management screens.  
`administration-tool/` remains a separate service.

## Run locally

1. Install dependencies:
   - `pip install -r frontend/requirements.txt`
2. Set environment variables:
   - `FRONTEND_SECRET_KEY` (required)
   - `BACKEND_API_URL` (default: `http://127.0.0.1:5000`)
   - `PLAY_SERVICE_PUBLIC_URL` (default: `http://127.0.0.1:8001`)
   - `FRONTEND_PORT` (default: `5002`)
3. Start:
   - `python frontend/run.py`

## Environment variables

- `FRONTEND_SECRET_KEY`: frontend session signing key
- `BACKEND_API_URL`: backend API base URL
- `PLAY_SERVICE_PUBLIC_URL`: public play-service URL used by play shell
- `FRONTEND_PORT` / `PORT`: bind port
- `PREFER_HTTPS`: enables secure session cookies
