# Testing Guide — World of Shadows Backend

Complete documentation for running the backend test suite.

## Quick Start

### Using Bash Script (Linux/macOS)
```bash
cd tests
./run_tests.sh              # Full suite with coverage
./run_tests.sh quick        # Fast tests (no coverage)
./run_tests.sh coverage     # Detailed coverage report
```

### Using Python (Cross-Platform)
```bash
cd tests
python run_tests.py         # Full suite with coverage
python run_tests.py --quick # Fast tests (no coverage)
python run_tests.py --help  # Show options
```

### Using Make (If installed)
```bash
cd tests
make test               # Full suite (default)
make test-quick        # Fast tests
make test-coverage     # Detailed coverage
make help              # Show all targets
```

---

## Test Modes

### Full Test Suite (Default)
Runs all tests with code coverage reporting.

```bash
./run_tests.sh
# or
python run_tests.py
```

**What it does:**
- Discovers and runs all test files (`test_*.py`)
- Generates coverage report
- Fails if coverage < 85%
- Outputs HTML coverage report to `htmlcov/`

**Typical duration:** 2-5 minutes

---

### Quick Tests
Fast test run without coverage checking — useful during development.

```bash
./run_tests.sh quick
# or
python run_tests.py --quick
```

**What it does:**
- Runs all tests
- Stops on first failure (`-x`)
- No coverage reporting
- Minimal output

**Typical duration:** 30-90 seconds

---

### Coverage Report
Detailed coverage analysis with skipped lines highlighted.

```bash
./run_tests.sh coverage
# or
python run_tests.py --coverage
```

**What it does:**
- Full test run with coverage
- Shows missing lines for each module
- Generates HTML report (`htmlcov/index.html`)
- Generates JSON report for CI/CD

**Output example:**
```
app/services/user_service.py    94%    lines 42, 98, 150
app/api/auth_routes.py          88%    lines 23-25, 67
...
```

---

### API Tests Only
Runs tests related to API endpoints.

```bash
./run_tests.sh api
# or
python run_tests.py --api
```

**What it does:**
- Filters to tests with "api" in name or path
- Examples: `test_api.py`, `test_*_api*.py`
- No coverage reporting

**Typical duration:** 30 seconds

---

### Security Tests
Runs security-focused tests (authentication, authorization, vulnerabilities).

```bash
./run_tests.sh security
# or
python run_tests.py --security
```

**What it does:**
- Filters to tests matching: `security`, `csrf`, `auth`, `injection`, `xss`, `privilege`
- Tests authentication flows, input validation, authorization
- No coverage reporting

**Test files included:**
- `test_auth_*.py`
- `test_csrf_*.py`
- `test_*_injection.py`
- `test_xss_*.py`
- `test_admin_security.py`

**Typical duration:** 45 seconds

---

### Verbose Mode
Full debug output with long tracebacks.

```bash
./run_tests.sh verbose
# or
python run_tests.py --verbose
```

**What it does:**
- Very verbose output (`-vv`)
- Long tracebacks (`--tb=long`)
- No output capture (`-s`) — see print() statements
- Coverage reporting enabled

**Use when:**
- Debugging a failing test
- Need to see print/logging output
- Want detailed error messages

**Typical duration:** 2-5 minutes

---

## Coverage Reports

### View Coverage in Browser
After running `test-coverage` or `test`:

```bash
# On Linux/macOS
open backend/htmlcov/index.html

# On Windows
start backend\htmlcov\index.html

# Using Python (cross-platform)
python -m webbrowser backend/htmlcov/index.html

# Or with make
make coverage-html
```

### Coverage Requirements
- **Minimum:** 85% of code must be covered
- **Threshold:** Tests fail if coverage drops below threshold
- **Exclusions:** Some lines may be marked as unreachable or don't-count-this

### Understanding Coverage Report
The HTML report shows:
- **Green:** Covered (code was executed during tests)
- **Red:** Not covered (code was never executed)
- **Yellow:** Partial (conditional branches not fully tested)

Click on file names to see line-by-line coverage.

---

## Failure Reports

When tests fail, the runners automatically generate a detailed failure report saved to `reports/`:

**Report filename:** `FAILED_TESTS_YYYYMMDD_HHMMSS.txt`

**Example:**
```
reports/FAILED_TESTS_20260324_143022.txt
```

### Report Contents

Each failure report includes:

- **Total failures:** Count of all failed tests
- **Test names:** Full test identifier (e.g., `test_api.py::TestUser::test_login`)
- **Error messages:** Assertion failure or exception message
- **Full traceback:** Complete error details for debugging

### Example Report Output

```
══════════════════════════════════════════════════════════════════════════════
FAILED TESTS REPORT
══════════════════════════════════════════════════════════════════════════════
Total failures: 3
══════════════════════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────────────────────
[1] test_api.py::TestAuth::test_login_fails_with_invalid_password
────────────────────────────────────────────────────────────────────────────
Message: AssertionError: Expected 401, got 200

Details:
test_api.py:123: in test_login_fails_with_invalid_password
    assert response.status_code == 401
AssertionError: assert 200 == 401

────────────────────────────────────────────────────────────────────────────
[2] test_auth_permissions.py::TestPrivilege::test_user_cannot_escalate
────────────────────────────────────────────────────────────────────────────
Message: AssertionError: Expected privilege check to reject elevation

Details:
...

══════════════════════════════════════════════════════════════════════════════
Summary: 3 test(s) failed
══════════════════════════════════════════════════════════════════════════════
```

### Accessing Failure Reports

Reports are automatically printed to the console with their file path:
```
📄 Failed tests report saved to: tests/reports/FAILED_TESTS_20260324_143022.txt
```

You can also check the `tests/reports/` directory:
```bash
cd tests
ls -lh reports/
tail -f reports/FAILED_TESTS_*.txt
```

---

## Test Organization

### Directory Structure
```
tests/
├── test_api.py                        # General API tests
├── test_auth_*.py                     # Authentication tests
├── test_csrf_*.py                     # CSRF protection tests
├── test_*_injection.py                # SQL injection tests
├── test_*_security.py                 # Security-focused tests
├── test_admin_*.py                    # Admin endpoint tests
├── test_forum_*.py                    # Forum feature tests
├── test_news_*.py                     # News feature tests
├── test_data_*.py                     # Data import/export tests
├── conftest.py                        # Pytest fixtures (app, client, user)
├── pytest.ini                         # Pytest configuration
├── reports/                           # Test failure reports (auto-generated)
│   └── FAILED_TESTS_*.txt             # Timestamped failure reports
├── run_tests.sh                       # Bash test runner
├── run_tests.py                       # Python test runner (cross-platform)
├── Makefile                           # Make shortcuts
├── TESTING.md                         # This file
└── ... (70+ test files)
```

### Key Test Files
| File | Purpose |
|------|---------|
| `conftest.py` | Shared fixtures (app, test_user, client) |
| `test_api.py` | General API functionality |
| `test_auth_permissions.py` | Authentication & authorization |
| `test_csrf_protection.py` | CSRF token validation |
| `test_*_injection.py` | SQL injection prevention |
| `test_admin_security.py` | Admin endpoint security |
| `test_*_security.py` | Vulnerability-specific tests |

---

## Common Issues & Fixes

### `pytest: command not found`
**Solution:**
```bash
pip install -r requirements-dev.txt
```

### Tests fail with "no module named 'app'"
**Solution:** Make sure you're in the `backend/tests/` directory
```bash
cd tests
python run_tests.py
```

### Coverage below 85% threshold
**Options:**
1. Write tests for uncovered lines
2. Temporarily skip with `make test-quick` (no coverage check)
3. Check `htmlcov/index.html` to see what's missing

### Slow test runs
**Use quick mode:**
```bash
./run_tests.sh quick
# or
make test-quick
```

### Test hangs or times out
**Likely cause:** Database lock or long-running fixture
- Use `Ctrl+C` to interrupt
- Check for background processes: `ps aux | grep python`
- Run single test: `pytest tests/test_specific.py`

### Import errors in tests
**Solution:**
```bash
# Make sure dependencies are installed
pip install -r requirements-dev.txt

# Verify Flask app initializes
python -c "from app import create_app; app = create_app(); print('OK')"
```

---

## CI/CD Integration

### GitHub Actions
Example workflow (`.github/workflows/test.yml`):
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r backend/requirements-dev.txt
      - run: cd backend && python run_tests.py --coverage
```

### Local Pre-commit Hook
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
cd backend
python run_tests.py --quick
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Configuration

### pytest.ini
Controls pytest behavior:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short --cov=app --cov-report=term-missing --cov-fail-under=85
filterwarnings =
    ignore::sqlalchemy.exc.LegacyAPIWarning
```

### Custom Configuration
Create `pytest.ini.local` to override for your environment:
```ini
[pytest]
testpaths = tests
addopts = -v --tb=short --cov=app --cov-report=html
```

---

## Advanced Usage

### Run Single Test File
```bash
python -m pytest tests/test_api.py -v
```

### Run Single Test Function
```bash
python -m pytest tests/test_api.py::test_health_check -v
```

### Run Tests Matching Pattern
```bash
python -m pytest -k "auth" -v
# Runs all tests with 'auth' in the name
```

### Run with Markers
```bash
python -m pytest -m security -v
# (If tests are marked with @pytest.mark.security)
```

### Parallel Testing (faster)
```bash
pip install pytest-xdist
pytest -n auto  # Use all CPU cores
```

### Interactive Debugging
```bash
python -m pytest tests/test_api.py --pdb -s
# Drops into debugger on failure, shows print output
```

---

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Flask Testing](https://flask.palletsprojects.com/testing/)
- [SQLAlchemy Testing Patterns](https://docs.sqlalchemy.org/testing/)

---

## Questions?

For issues or questions about testing:
1. Check the test file directly: `backend/tests/test_*.py`
2. Review `conftest.py` for available fixtures
3. Run in verbose mode: `python run_tests.py --verbose`
4. Check pytest output for specific error messages
