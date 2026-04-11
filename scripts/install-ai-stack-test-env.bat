@echo off
REM Thin wrapper: same as CI / install-ai-stack-test-env.ps1
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-ai-stack-test-env.ps1" %*
exit /b %ERRORLEVEL%
