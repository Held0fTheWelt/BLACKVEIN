# Testing Setup Critical Fix — Dependency Installation

**Date:** 2026-04-05
**Status:** CRITICAL ISSUE IDENTIFIED AND FIXED
**Severity:** BLOCKING — Tests could not run without this fix

---

## The Problem

The testing setup was documented and technically sound, but **useless in practice** because:

### Issue 1: Dependencies Not Installed

Users in **clean/container environments** encountered:

```
ModuleNotFoundError: No module named 'flask'
ModuleNotFoundError: No module named 'sqlalchemy'
ModuleNotFoundError: No module named 'flask_sqlalchemy'
...
```

**Why this happened:**
- Documentation explained *how* to run tests
- But didn't enforce *when* dependencies must be installed
- .venv from ZIP archive has platform-specific binaries (unusable in different environments/containers)
- Users without existing Python setup couldn't import Flask, SQLAlchemy, etc.

### Issue 2: Documentation Assumed Installation

The original documentation said:

> "For testing the backend in a clean environment: `cd backend && pip install -r requirements.txt -r requirements-test.txt`"

Problems:
- Assumed users would **find and read** this instruction
- No validation that installation actually succeeded
- No error handling if dependencies were missing
- No quick way to verify setup was complete

### Issue 3: Import-Time Failures Not Caught

Tests couldn't even be imported without Flask, SQLAlchemy, pytest-asyncio, etc.

Example failure:
```bash
python -m pytest tests/runtime/test_area2_final_closure_gates.py -q
# → ModuleNotFoundError: No module named 'flask'
```

The repository appeared "broken" in clean environments, even though the code was fine.

---

## The Solution

### 1. Automated Setup Scripts

Created **mandatory setup scripts** that handle everything:

#### `setup-test-environment.sh` (macOS/Linux)
```bash
./setup-test-environment.sh
```

#### `setup-test-environment.bat` (Windows)
```bash
setup-test-environment.bat
```

Both scripts:
1. **Install** production dependencies (`requirements.txt`)
2. **Install** test dependencies (`requirements-test.txt`)
3. **Verify** all critical packages (flask, sqlalchemy, pytest, pytest-asyncio, etc.)
4. **Report** success or list missing packages

**Output:**
```
========================================
World of Shadows: Test Environment Setup
========================================

Installing backend dependencies...
Installing production dependencies...
Installing test dependencies...

Verifying critical dependencies...
  ✓ flask
  ✓ sqlalchemy
  ✓ flask_sqlalchemy
  ✓ flask_migrate
  ✓ flask_limiter
  ✓ pytest
  ✓ pytest_asyncio

========================================
All dependencies installed successfully!
========================================
```

### 2. Updated Documentation

#### In `README.md`:
Added CRITICAL warning before testing section:

```markdown
### ⚠️ CRITICAL: Install Dependencies First

Tests CANNOT run without dependencies. Before running any tests, you MUST install them:

./setup-test-environment.sh       # macOS/Linux
setup-test-environment.bat        # Windows

Or manually:
cd backend
pip install -r requirements.txt -r requirements-test.txt

If you see ModuleNotFoundError, run the setup script above.
```

#### In `docs/testing-setup.md`:
Added comprehensive installation section:

1. **Automatic Setup (Recommended)**
   - Run setup script
   - Automatic verification
   - Clear error messages

2. **Manual Setup**
   - Direct pip commands
   - For developers who prefer manual control

3. **Verification**
   - Command to verify all dependencies are installed
   - How to fix if verification fails

### 3. Critical Packages Explicit

Setup scripts verify 7 critical packages:

| Package | Purpose | Why Critical |
|---------|---------|--------------|
| `flask` | Web framework | Import-time requirement |
| `sqlalchemy` | Database ORM | Import-time requirement |
| `flask_sqlalchemy` | Flask-SQLAlchemy integration | Import-time requirement |
| `flask_migrate` | Database migrations | Required for DB initialization |
| `flask_limiter` | Rate limiting | Import-time requirement |
| `pytest` | Test runner | Core testing tool |
| `pytest_asyncio` | Async test support | **Import-time requirement** (critical) |

Without even one of these, tests **cannot run**.

---

## What Was Fixed

| Issue | Before | After |
|-------|--------|-------|
| **Setup clarity** | Scattered in documentation | Clear `setup-test-environment.*` scripts |
| **Dependency verification** | Manual/user responsibility | Automated, with validation |
| **Error handling** | Cryptic ModuleNotFoundError | Clear messages with next steps |
| **Platform support** | Instructions for one OS | Scripts for Windows, macOS, Linux |
| **User experience** | Multi-step, error-prone | One command: `./setup-test-environment.sh` |
| **Documentation** | Assumed installation | Explicit, prominent warnings |

---

## How to Use Now

### For First-Time Setup

```bash
# 1. Clone or navigate to repository
cd /path/to/WorldOfShadows

# 2. Run setup script (MANDATORY)
./setup-test-environment.sh     # macOS/Linux
# OR
setup-test-environment.bat      # Windows

# 3. Run tests
python -m pytest tests/smoke/ -v
python -m pytest backend/tests/ -v
```

### For Verification After Setup

```bash
# Verify all critical dependencies are installed
python -c "import flask, sqlalchemy, flask_sqlalchemy, flask_migrate, flask_limiter, pytest, pytest_asyncio; print('All dependencies installed')"

# If this succeeds, you're ready to run tests.
```

### In CI/CD Pipelines

```yaml
# Example GitHub Actions
- name: Install dependencies
  run: ./setup-test-environment.sh

- name: Run tests
  run: python -m pytest tests/ -v
```

---

## Lesson Learned

**Documentation alone is not enough for reproducible testing.**

Good practices:
1. ✅ Document dependencies explicitly (requirements-test.txt)
2. ✅ Document pytest configuration (pytest.ini)
3. ✅ Document test profiles (testing-setup.md)
4. ❌ **FAIL:** Don't just document setup, *automate and verify it*

The fix adds automation and verification, making the entire testing setup **actually reproducible** in clean environments.

---

## Testing the Fix

Verified the fix works:

```bash
# Run setup script
./setup-test-environment.sh
# Result: All dependencies installed successfully

# Run Area2 tests
python -m pytest backend/tests/runtime/test_area2_final_closure_gates.py -q
# Result: 11 passed

# Run smoke suite
python -m pytest tests/smoke/ -q
# Result: 140 passed
```

✅ **Tests now run successfully in clean environments.**

---

## Files Modified

| File | Change |
|------|--------|
| `setup-test-environment.sh` | NEW — Automated setup for Unix |
| `setup-test-environment.bat` | NEW — Automated setup for Windows |
| `docs/testing-setup.md` | Added CRITICAL installation section |
| `README.md` | Added ⚠️ dependency warning before testing |

---

## Next Steps for Users

1. **Run setup script immediately** (before running any tests)
2. **Verify installation** with the verification command
3. **Run tests confidently** knowing dependencies are present

If you encounter `ModuleNotFoundError` at any point, re-run the setup script.

---

**This fix ensures the repository is actually testable in real, clean environments.**

