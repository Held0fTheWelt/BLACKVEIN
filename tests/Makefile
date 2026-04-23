.PHONY: test test-quick test-coverage test-playwright test-compose-smoke test-contracts test-integration test-help install-deps clean

.DEFAULT_GOAL := test

PYTHON ?= python3

test:
	@echo "Running all Python suite groups..."
	@$(PYTHON) run_tests.py

test-quick:
	@echo "Quick run (no coverage, stop on first failure)..."
	@$(PYTHON) run_tests.py --quick

test-coverage:
	@echo "Full run with detailed coverage reports (where enabled)..."
	@$(PYTHON) run_tests.py --coverage

test-playwright:
	@echo "Run full Python suite groups + Playwright lane..."
	@$(PYTHON) run_tests.py --with-playwright

test-compose-smoke:
	@echo "Run full Python suite groups + compose smoke lane..."
	@$(PYTHON) run_tests.py --with-compose-smoke

test-contracts:
	@$(PYTHON) run_tests.py --suite backend --scope contracts

test-integration:
	@$(PYTHON) run_tests.py --suite backend --scope integration

test-help:
	@$(PYTHON) run_tests.py --help

install-deps:
	@echo "Install dev dependencies from each component as needed, e.g.:"
	@echo "  pip install -r ../backend/requirements-dev.txt"

clean:
	@echo "Cleaning test artifacts under tests/..."
	@rm -rf .pytest_cache htmlcov .coverage __pycache__ reports/*.xml 2>/dev/null || true
	@echo "Done."

help:
	@echo "World of Shadows — test runner (tests/run_tests.py)"
	@echo ""
	@echo "  make test              - All Python suite groups (default)"
	@echo "  make test-quick        - Quick, no coverage"
	@echo "  make test-coverage     - Full run + HTML coverage"
	@echo "  make test-playwright   - Full Python run + Playwright lane"
	@echo "  make test-compose-smoke- Full Python run + compose smoke lane"
	@echo "  make test-contracts    - Backend only (marker: contract)"
	@echo "  make test-integration  - Backend only (marker: integration)"
	@echo "  make test-help         - Show run_tests.py --help"
	@echo "  make clean             - Remove local caches and reports"
	@echo ""
