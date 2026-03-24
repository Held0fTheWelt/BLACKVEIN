.PHONY: test test-quick test-coverage test-api test-security test-verbose test-help install-deps

# Default target
.DEFAULT_GOAL := test

# Test targets

test:
	@echo "Running full test suite with coverage..."
	@python3 run_tests.py

test-quick:
	@echo "Running quick tests (no coverage)..."
	@python3 run_tests.py --quick

test-coverage:
	@echo "Running with detailed coverage report..."
	@python3 run_tests.py --coverage

test-api:
	@echo "Running API tests only..."
	@python3 run_tests.py --api

test-security:
	@echo "Running security tests..."
	@python3 run_tests.py --security

test-verbose:
	@echo "Running tests with full debug output..."
	@python3 run_tests.py --verbose

test-help:
	@python3 run_tests.py --help

# Utility targets

install-deps:
	@echo "Installing test dependencies..."
	@pip install -r requirements-dev.txt

coverage-html:
	@echo "Opening coverage report..."
	@python3 -m webbrowser htmlcov/index.html || echo "Open htmlcov/index.html in your browser"

clean:
	@echo "Cleaning test artifacts..."
	@rm -rf .pytest_cache htmlcov .coverage __pycache__
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done."

# Help
help:
	@echo "World of Shadows — Test Runner"
	@echo ""
	@echo "Usage:"
	@echo "  make test              - Run full suite with coverage (default)"
	@echo "  make test-quick        - Run fast tests (no coverage)"
	@echo "  make test-coverage     - Full suite with detailed coverage"
	@echo "  make test-api          - API tests only"
	@echo "  make test-security     - Security tests only"
	@echo "  make test-verbose      - Full debug output"
	@echo "  make install-deps      - Install test dependencies"
	@echo "  make coverage-html     - Open coverage report"
	@echo "  make clean             - Remove test artifacts"
	@echo "  make help              - Show this message"
