# PythonAnywhere Setup Guide

## Quick Setup (One Command)

After deploying to PythonAnywhere, run this **once** in the Bash console:

```bash
cd ~/worldofshadows/backend
python setup_env.py
```

That's it! The script will:
1. ✓ Generate valid cryptographic keys for `SECRET_KEY` and `JWT_SECRET_KEY`
2. ✓ Create/update `.env` file with required configuration
3. ✓ Run all database migrations
4. ✓ Verify everything works

## What It Does

### Environment File (`.env`)
- Generates 32+ byte cryptographic keys using Python's `secrets` module
- Creates `.env` file if it doesn't exist
- Updates keys if they're too short or invalid
- **Does NOT overwrite existing valid keys**

### Database Migrations
- Runs `flask db upgrade` to create all required tables
- Creates 31 tables including users, forums, wiki pages, game data, etc.
- Idempotent — safe to run multiple times

### Verification
- Checks that `JWT_SECRET_KEY` is at least 32 bytes (256 bits)
- Verifies Flask app can initialize with the configuration

## Manual Steps (If Script Fails)

If the setup script fails, you can manually run each step:

### 1. Access PythonAnywhere Console

```bash
cd ~/worldofshadows/backend
```

### 2. Create `.env` File

```bash
cat > .env << 'EOF'
# Generated on deployment
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
JWT_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
FLASK_APP=run:app
FLASK_DEBUG=0
PORT=5000
EOF
```

Or use the Python script to generate keys:

```bash
python3 << 'EOF'
import secrets
print(f'SECRET_KEY={secrets.token_urlsafe(32)}')
print(f'JWT_SECRET_KEY={secrets.token_urlsafe(32)}')
EOF
```

### 3. Run Migrations

```bash
python -m flask db upgrade
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
```

### 4. Reload Web App

- Go to **Web** tab in PythonAnywhere dashboard
- Click **Reload** button next to your web app name
- Wait 30 seconds for app to restart

### 5. Test

Visit your domain in a browser and check:
- Homepage loads
- No 500 errors in the logs
- API endpoints respond (e.g., `/api/v1/health`)

## Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"

The virtual environment might not be active. On PythonAnywhere:
```bash
source /home/yourusername/.virtualenvs/yourenv/bin/activate
python setup_env.py
```

### "Permission denied" on `.env`

```bash
chmod 644 backend/.env
```

### Database still shows old migrations

The `.env` file is cached by your web app. After updating it:
1. Change `.env` file
2. Reload the web app from PythonAnywhere dashboard
3. Test again

### "JWT_SECRET_KEY must be at least 32 bytes"

Your `.env` still has the placeholder value. Run:
```bash
python setup_env.py
```

This will update it with a valid key.

## Verification Checklist

After running the setup script:

- [ ] Script completed without errors
- [ ] `.env` file exists at `~/worldofshadows/backend/.env`
- [ ] Web app reloaded in PythonAnywhere dashboard
- [ ] Homepage loads without 500 errors
- [ ] Check Error log shows no cryptography errors

## Database Location

The SQLite database is created at:
```
~/worldofshadows/backend/instance/wos.db
```

If you need to reset the database:
```bash
rm -f backend/instance/wos.db
python setup_env.py
```

This will recreate all tables from scratch.

## Environment Variables

The setup script manages these in `.env`:

| Variable | Purpose | Length |
|---|---|---|
| `SECRET_KEY` | Flask session secret | 32+ bytes |
| `JWT_SECRET_KEY` | JWT token signing | 32+ bytes |
| `FLASK_APP` | Entry point | - |
| `FLASK_DEBUG` | Debug mode (0=off) | - |
| `PORT` | Server port | - |

All other variables are optional and have sensible defaults.

## Need Help?

If the setup script doesn't work:
1. Check PythonAnywhere error log
2. Run `python setup_env.py` with verbose output
3. Verify Python version is 3.8+: `python --version`
4. Check virtual environment is activated
