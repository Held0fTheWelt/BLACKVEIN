# Gap Map / Wave Selection — 2026-04-21 (dependency closure update)

## Starting gaps addressed here

1. Missing Flask / SQLAlchemy runtime family
2. Missing LangChain / LangGraph runtime family
3. Frontend pytest import-path gap revealed after hydration
4. Backend smoke/plugin import-path gap revealed after hydration
5. Admin pytest path hardening for repeatable suite-local execution

## Wave chosen

The strongest justified wave was **environment hydration plus post-hydration boot-path repair**, because it removed the largest remaining blocker surface.

## Resulting status

- original dependency blocker family: **closed**
- embedding model acquisition: still residual
- broader runtime-proof expansion: still continuation work, but no longer blocked by the original dependency family
