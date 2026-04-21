@REM Setup test environment - installs all required dependencies (Windows)
@REM
@REM This script MUST be run before running any tests.
@REM It installs both production and test dependencies.
@REM
@REM Security / hygiene (automated test suites, ed4815d+):
@REM - Installs only from requirement files in this repository (relative paths after cd);
@REM   no remote pipe-to-shell bootstrap (only pip install -r from this tree).
@REM - Resolves ``PYTHON_EXE`` via the Windows ``py`` launcher first (avoids the broken
@REM   Microsoft Store ``WindowsApps\python.exe`` stub), then falls back to ``python``.
@REM - Uses ``"%PYTHON_EXE%" -m pip`` for installs.
@REM
@REM Usage:
@REM   setup-test-environment.bat

@SETLOCAL ENABLEDELAYEDEXPANSION
@ECHO OFF

setlocal enabledelayedexpansion

echo ========================================
echo World of Shadows: Test Environment Setup
echo ========================================
echo.

REM Get repository root (script directory)
set "REPO_ROOT=%~dp0"
cd /d "%REPO_ROOT%"

REM Resolve a real interpreter: prefer ``py -3.x`` over PATH ``python`` (Store stub).
set "PYTHON_EXE="
where py >nul 2>&1
if %errorlevel% equ 0 (
  for %%V in (3.13 3.12 3.11 3.10) do (
    if not defined PYTHON_EXE (
      py -%%V -c "import sys" >nul 2>&1
      if not errorlevel 1 (
        for /f "delims=" %%i in ('py -%%V -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%i"
      )
    )
  )
)
if not defined PYTHON_EXE (
  python -c "import sys" >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%i"
  )
)
if not defined PYTHON_EXE (
  echo Error: No usable Python interpreter found.
  echo Install Python 3.10+ from https://www.python.org/downloads/windows/ ^(include the py launcher^).
  echo If ``python`` is the Microsoft Store alias, disable it under:
  echo   Settings - Apps - Advanced app settings - App execution aliases
  exit /b 1
)

echo %PYTHON_EXE% | findstr /I "WindowsApps" >nul
if not errorlevel 1 (
  echo Error: Interpreter points at Microsoft WindowsApps ^(Store stub^), which cannot run here.
  echo Install CPython from https://www.python.org/downloads/windows/ and use ``py -3.13`` or pick:
  echo   Typical fix: %LocalAppData%\Programs\Python\Python313\python.exe
  exit /b 1
)

REM pip/build backends often spawn ``python`` from PATH; put this interpreter first.
for %%I in ("%PYTHON_EXE%") do set "PYTHON_DIR=%%~dpI"
set "PATH=%PYTHON_DIR%;%PYTHON_DIR%Scripts;%PATH%"

for /f "tokens=*" %%i in ('"%PYTHON_EXE%" --version') do set "PYTHON_VERSION=%%i"
echo Repository: %REPO_ROOT%
echo Python: %PYTHON_VERSION%
echo Executable: %PYTHON_EXE%
echo.

REM Install backend dependencies (same bar as .github/workflows/backend-tests.yml)
echo Installing backend dependencies...
cd backend

if not exist "requirements-dev.txt" (
    echo Error: backend/requirements-dev.txt not found
    exit /b 1
)

echo Installing production and dev/test dependencies via requirements-dev.txt...
"%PYTHON_EXE%" -m pip install --upgrade pip -q
if errorlevel 1 (
    echo Error upgrading pip
    exit /b 1
)

"%PYTHON_EXE%" -m pip install -r requirements-dev.txt -q
if errorlevel 1 (
    echo Error installing dependencies
    exit /b 1
)

cd /d "%REPO_ROOT%"

REM Other components for ``python tests/run_tests.py --suite all``
if exist "frontend\requirements-dev.txt" (
    echo Installing frontend test dependencies...
    "%PYTHON_EXE%" -m pip install -r frontend/requirements-dev.txt -q
    if errorlevel 1 exit /b 1
)
if exist "administration-tool\requirements-dev.txt" (
    echo Installing administration-tool test dependencies...
    python -m pip install -r administration-tool/requirements-dev.txt -q
    if errorlevel 1 exit /b 1
)
if exist "world-engine\requirements-dev.txt" (
    echo Installing world-engine test dependencies...
    "%PYTHON_EXE%" -m pip install -r world-engine/requirements-dev.txt -q
    if errorlevel 1 exit /b 1
)

REM Editable local packages so ai_stack LangGraph tests and imports match CI / full repo layout.
if exist "story_runtime_core\pyproject.toml" (
    echo Installing story_runtime_core ^(editable^)...
    "%PYTHON_EXE%" -m pip install -e "./story_runtime_core" -q
    if errorlevel 1 (
        echo Error: editable install of story_runtime_core failed
        echo Fix pyproject.toml / setuptools layout, then retry.
        exit /b 1
    )
)
if exist "ai_stack\pyproject.toml" (
    echo Installing ai_stack[test] ^(editable — langchain-core, langgraph, ...^)...
    "%PYTHON_EXE%" -m pip install -e "./ai_stack[test]" -q
    if errorlevel 1 (
        echo Error: editable install of ai_stack[test] failed
        exit /b 1
    )
)

echo Ensuring Python 3.14-safe pytest-asyncio range...
"%PYTHON_EXE%" -m pip install --upgrade "pytest-asyncio>=1.3,<2" -q
if !errorlevel! neq 0 (
    echo Error: pytest-asyncio upgrade failed
    exit /b 1
)

REM Verify critical dependencies
echo.
echo Verifying critical dependencies...

set "MISSING="

for %%p in (flask sqlalchemy flask_sqlalchemy flask_migrate flask_limiter pytest pytest_asyncio langchain_core langgraph fastapi httpx) do (
    "%PYTHON_EXE%" -c "import %%p" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   [OK] %%p
    ) else (
        echo   [MISSING] %%p
        set "MISSING=!MISSING! %%p"
    )
)

echo.

if "!MISSING!" NEQ "" (
    echo Error: Missing required packages:
    echo   !MISSING!
    echo.
    echo Try running pip install again from repo root - see setup-test-environment.bat
    exit /b 1
)

echo Verifying ai_stack LangGraph export RuntimeTurnGraphExecutor...
set "PYTHONPATH=%REPO_ROOT%"
"%PYTHON_EXE%" "%REPO_ROOT%scripts\verify_ai_stack_test_env.py"
if errorlevel 1 (
    echo Error: ai_stack LangGraph export check failed.
    echo Ensure: pip install -e ./story_runtime_core ^&^& pip install -e "./ai_stack[test]"
    exit /b 1
)

echo ========================================
echo All dependencies installed successfully!
echo ========================================
echo.
echo Full Python orchestrator from repo root:
echo   "%PYTHON_EXE%" tests/run_tests.py
echo Or component-only:
echo   "%PYTHON_EXE%" -m pytest tests/smoke/ -v
echo   "%PYTHON_EXE%" -m pytest backend/tests/ -v
echo   set PYTHONPATH=%%REPO_ROOT%% ^&^& "%PYTHON_EXE%" -m pytest ai_stack/tests -q
echo.
exit /b 0
