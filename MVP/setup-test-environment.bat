@REM Setup test environment - installs all required dependencies (Windows)
@REM
@REM This script MUST be run before running any tests.
@REM It installs both production and test dependencies.
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

REM Check if python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    echo Please install Python 3.10+ and try again.
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set "PYTHON_VERSION=%%i"
echo Repository: %REPO_ROOT%
echo Python: %PYTHON_VERSION%
echo.

REM Install backend dependencies
echo Installing backend dependencies...
cd backend

if not exist "requirements.txt" (
    echo Error: backend/requirements.txt not found
    exit /b 1
)

if not exist "requirements-test.txt" (
    echo Error: backend/requirements-test.txt not found
    exit /b 1
)

echo Installing production and test dependencies via requirements-test.txt...
python -m pip install --upgrade pip -q
if errorlevel 1 (
    echo Error upgrading pip
    exit /b 1
)

python -m pip install -r requirements-test.txt -q
if errorlevel 1 (
    echo Error installing dependencies
    exit /b 1
)

cd /d "%REPO_ROOT%"

REM Editable local packages so ai_stack LangGraph tests and imports match CI / full repo layout.
if exist "story_runtime_core\pyproject.toml" (
    echo Installing story_runtime_core ^(editable^)...
    python -m pip install -e "./story_runtime_core" -q
    if errorlevel 1 (
        echo Error: editable install of story_runtime_core failed
        echo Fix pyproject.toml / setuptools layout, then retry.
        exit /b 1
    )
)
if exist "ai_stack\pyproject.toml" (
    echo Installing ai_stack[test] ^(editable — langchain-core, langgraph, ...^)...
    python -m pip install -e "./ai_stack[test]" -q
    if errorlevel 1 (
        echo Error: editable install of ai_stack[test] failed
        exit /b 1
    )
)

REM Verify critical dependencies
echo.
echo Verifying critical dependencies...

setlocal enabledelayedexpansion
set "MISSING="

for %%p in (flask sqlalchemy flask_sqlalchemy flask_migrate flask_limiter pytest pytest_asyncio langchain_core langgraph) do (
    python -c "import %%p" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   [OK] %%p
    ) else (
        echo   [MISSING] %%p
        set "MISSING=!MISSING! %%p"
    )
)

echo.

if not "!MISSING!"=="" (
    echo Error: Missing required packages:
    echo   !MISSING!
    echo.
    echo Try running pip install again:
    echo   pip install -r backend/requirements.txt -r backend/requirements-test.txt
    exit /b 1
)

echo ========================================
echo All dependencies installed successfully!
echo ========================================
echo.
echo You can now run tests:
echo   python -m pytest tests/smoke/ -v
echo   python -m pytest backend/tests/ -v
echo   set PYTHONPATH=%%REPO_ROOT%% ^&^& python -m pytest ai_stack/tests -q
echo.
exit /b 0
