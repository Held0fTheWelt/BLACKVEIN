# Single Test Runner Enforcement

**Generated:** 2026-04-26

---

## Enforcement Status: COMPLIANT

The repository now has exactly one canonical test runner:

```
tests/run_tests.py
```

---

## Root Runner Removal

| Before | After |
|--------|-------|
| tests/run_tests.py present at repo root | DELETED |
| tests/run_tests.py | ACTIVE |

`tests/run_tests.py` was deleted on 2026-04-26.

---

## Canonical Runner Contract

`tests/run_tests.py` must be invoked as:

```bash
python tests/run_tests.py                    # Run all suites
python tests/run_tests.py --suite engine     # Run one suite
python tests/run_tests.py --suite all        # Explicit all
python tests/run_tests.py --suite all --quick  # Quick mode
```

---

## Suite Sequence (ALL_SUITE_SEQUENCE)

Current sequence for `--suite all`:

1. backend
2. frontend
3. administration
4. engine
5. database
6. ai_stack
7. story_runtime_core
8. gates
9. root_core
10. root_integration
11. root_branching
12. root_smoke
13. root_tools
14. root_requirements_hygiene
15. root_e2e_python
16. root_experience_scoring

Optional (not in all): playwright_e2e, compose_smoke

---

## Verification

To verify single runner enforcement:

```bash
# Verify root runner is absent
ls tests/run_tests.py 2>/dev/null && echo "ERROR: root runner present" || echo "OK: root runner absent"
ls run-tests.py 2>/dev/null && echo "ERROR: root runner present" || echo "OK: root runner absent"
ls run_tests.py 2>/dev/null && echo "ERROR: root runner present" || echo "OK: root runner absent"

# Verify canonical runner exists
ls tests/run_tests.py && echo "OK: canonical runner present"
```
