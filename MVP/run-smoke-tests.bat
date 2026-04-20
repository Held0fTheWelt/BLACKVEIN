@REM Canonical smoke test runner for World of Shadows (Windows)
@REM
@REM This script runs the official smoke test suite to validate repository health
@REM in clean and development environments.
@REM
@REM Usage:
@REM   run-smoke-tests.bat              # Run full smoke suite (140 tests)
@REM   run-smoke-tests.bat --quick      # Run fast smoke tests only
@REM   run-smoke-tests.bat --verbose    # Run with detailed output
@REM
@REM What it validates:
@REM   - Backend startup and initialization (no errors)
@REM   - Database connectivity and schema
@REM   - Runtime routing bootstrap and initialization
@REM   - Content module YAML validity and consistency
@REM   - Core API endpoints (health checks)
@REM
@REM Exit codes:
@REM   0 - All smoke tests passed
@REM   1 - Some smoke tests failed
@REM   2 - Missing dependencies or configuration error

@SETLOCAL ENABLEDELAYEDEXPANSION
@ECHO OFF

set "VERBOSE="
set "QUICK="

REM Parse arguments
:parse_args
if "%1"=="" goto done_parsing
if "%1"=="--verbose" (
    set "VERBOSE=--verbose"
    shift
    goto parse_args
)
if "%1"=="-v" (
    set "VERBOSE=--verbose"
    shift
    goto parse_args
)
if "%1"=="--quick" (
    set "QUICK=true"
    shift
    goto parse_args
)
if "%1"=="-q" (
    set "QUICK=true"
    shift
    goto parse_args
)
if "%1"=="--help" (
    echo Usage: %0 [--verbose] [--quick] [--help]
    echo.
    echo Options:
    echo   --verbose, -v   Run with detailed output
    echo   --quick, -q     Run fast smoke tests only
    echo   --help, -h      Show this help message
    exit /b 0
)
if "%1"=="-h" (
    echo Usage: %0 [--verbose] [--quick] [--help]
    echo.
    echo Options:
    echo   --verbose, -v   Run with detailed output
    echo   --quick, -q     Run fast smoke tests only
    echo   --help, -h      Show this help message
    exit /b 0
)
echo Unknown option: %1
exit /b 2

:done_parsing

REM Check if pytest is available
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo Error: pytest not installed
    echo Run: pip install -r backend/requirements-test.txt
    exit /b 2
)

REM Get repository root (script directory)
set "REPO_ROOT=%~dp0"
cd /d "%REPO_ROOT%"

echo ===============================================
echo World of Shadows: Canonical Smoke Test Suite
echo ===============================================
echo.
echo Repository: %REPO_ROOT%
for /f "tokens=*" %%i in ('python --version') do set "PYTHON_VERSION=%%i"
echo Python: %PYTHON_VERSION%
for /f "tokens=*" %%i in ('python -m pytest --version') do set "PYTEST_VERSION=%%i"
echo Pytest: %PYTEST_VERSION%
echo.

REM Build pytest command
set "PYTEST_CMD=python -m pytest tests/smoke/"

if "!VERBOSE!"=="" (
    set "PYTEST_CMD=!PYTEST_CMD! -v"
) else (
    set "PYTEST_CMD=!PYTEST_CMD! -vv"
)

set "PYTEST_CMD=!PYTEST_CMD! --tb=short"

REM Add quick filter if requested
if "!QUICK!"=="true" (
    set "PYTEST_CMD=!PYTEST_CMD! -m "not slow""
    echo Running fast smoke tests only...
    echo.
) else (
    echo Running full smoke test suite...
    echo.
)

REM Run the smoke tests
%PYTEST_CMD%
if errorlevel 1 (
    echo.
    echo ===============================================
    echo X Smoke tests FAILED
    echo ===============================================
    echo.
    echo Review the output above for details.
    echo See docs\testing-setup.md for troubleshooting.
    exit /b 1
)

echo.
echo ===============================================
echo + Smoke tests PASSED
echo ===============================================
echo.
echo Repository health: GOOD
echo All core systems are initialized and responding.
exit /b 0
