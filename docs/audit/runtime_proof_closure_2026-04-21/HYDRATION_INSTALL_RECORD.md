# Hydration / Install Record — 2026-04-21

## Environment assumptions

- Python executable: `/opt/pyvenv/bin/python`
- Python version: `3.13.5`
- Package index available from this environment
- No claim made that arbitrary external model-host DNS is available

## Exact manifests used

- `backend/requirements-test.txt`
- `story_runtime_core/pyproject.toml`
- `ai_stack/pyproject.toml`
- root `pyproject.toml`

## Exact commands run

```bash
python -m pip install -r backend/requirements-test.txt
python -m pip install -e ./story_runtime_core
python -m pip install -e './ai_stack[test]'
python -m pip install -e .
```

## Installed / verified versions

```text
Flask==3.1.3
SQLAlchemy==2.0.49
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.1.0
Flask-Limiter==3.12
langchain==1.2.15
langchain-core==1.3.0
langgraph==1.1.8
fastembed==0.8.0
world-of-shadows-hub==0.0.0
```

## Version/conflict notes

During hydration, pip emitted a pre-existing environment warning:

- `gradio 6.5.1 requires starlette<1.0,>=0.40.0, but you have starlette 1.0.0`

This warning did **not** block the World of Shadows validations executed in this continuation.
