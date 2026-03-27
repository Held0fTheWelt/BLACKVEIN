# Development Guide

Setup, workflow, and best practices for local development.

## Getting Started

### 1️⃣ [Local Development Setup](./LocalDevelopment.md)
Complete guide to setting up the development environment on your machine.

**Quick Start:**
```bash
# Clone and install dependencies
git clone https://github.com/your-org/worldofshadows.git
cd WorldOfShadows
python -m pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run migrations
cd backend && flask db upgrade && cd ..

# Run tests (from tests/)
cd tests && python run_tests.py --suite all
cd ..
# Start development servers (see runbooks per service)
```

**Services:**
- Backend: `http://localhost:5000`
- Administration Tool: `http://localhost:5001`
- World Engine: `http://localhost:5002`

### 2️⃣ Project Structure
```
WorldOfShadows/
├── backend/                 # Flask backend API
│   ├── app/
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/       # Business logic
│   │   ├── routes/         # API endpoints
│   │   └── extensions.py   # Flask extensions
│   ├── migrations/         # Alembic schema migrations
│   └── tests/              # Backend test suite
│
├── administration-tool/     # Flask frontend
│   ├── app.py              # Main app
│   ├── templates/          # Jinja2 templates
│   ├── static/             # CSS, JS, images
│   └── tests/              # Frontend test suite
│
├── world-engine/           # FastAPI game runtime
│   ├── app/
│   │   ├── api/            # HTTP & WebSocket endpoints
│   │   ├── runtime/        # Game engine
│   │   └── auth/           # Ticket authentication
│   └── tests/              # Engine test suite
│
└── docs/                   # This documentation
```

## Common Development Tasks

### Running Tests

**All tests:**
```bash
cd tests
python run_tests.py --suite all
```

**Specific suite:**
```bash
cd tests
python run_tests.py --suite backend
python run_tests.py --suite administration
python run_tests.py --suite engine
python run_tests.py --suite database
```

**Specific test file:**
```bash
cd backend && pytest tests/test_auth.py -v
cd administration-tool && pytest tests/test_routes.py -v
cd world-engine && pytest tests/test_api.py -v
```

**See:** [tests/TESTING.md](../../tests/TESTING.md) (runner), [Testing docs index](../testing/README.md)

### Database Migrations

**Create new migration:**
```bash
cd backend
flask db migrate -m "Add new_column to users table"
# Edit migrations/versions/XXX_add_new_column.py
flask db upgrade
```

**See:** [Database Guide](../database/README.md)

### Running Services

**Backend only:**
```bash
cd backend && FLASK_APP=run:app python -m flask run
```

**Administration tool:**
```bash
cd administration-tool && python app.py
```

**World Engine:**
```bash
cd world-engine && python app.py
```

## Development Best Practices

### Code Style
- Python: Follow PEP 8 (linted by flake8)
- JavaScript: Follow Airbnb style guide
- SQL: Use parameterized queries only

### Testing Requirements
- All new code must include tests
- Minimum 80% code coverage required
- Test both success and failure paths
- See [Testing Guide](../testing/README.md)

### Git Workflow
1. Create feature branch: `git checkout -b feat/my-feature`
2. Write tests first (TDD)
3. Implement feature
4. Run full test suite: `python run_tests.py --suite all`
5. Commit: `git commit -m "feat: add my feature"`
6. Push: `git push origin feat/my-feature`
7. Create pull request

### Debugging

**Print debugging:**
```python
# Backend
app.logger.debug(f"Variable value: {var}")

# Frontend (Jinja2)
{{ variable|safe }}  {# Shows in HTML source #}

# World Engine (FastAPI)
import logging
logging.debug(f"Debug message: {data}")
```

**Using pdb:**
```python
import pdb; pdb.set_trace()  # Python debugger
```

**Environment variables:**
- `FLASK_ENV=development` - Flask dev mode
- `FLASK_DEBUG=1` - Auto-reload and debugger
- `LOG_LEVEL=DEBUG` - Verbose logging

## Architecture References

- [System Architecture](../architecture/README.md)
- [API Endpoints](../api/README.md)
- [Security Guidelines](../security/README.md)
- [Database Schema](../database/README.md)

## Troubleshooting

### Port already in use
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or use different port
FLASK_PORT=5010 python -m flask run
```

### Database errors
```bash
# Reset database (WARNING: deletes data!)
cd backend
rm instance/wos.db
flask db upgrade
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Tests failing
1. Check logs: `tail -f logs/*.log`
2. Run single test with verbose: `pytest tests/test_file.py::test_name -vv`
3. Check environment: `flask shell` then `print(current_app.config)`

---

**Still stuck?** Check the [Development Guide](#debugging) or ask the team.
