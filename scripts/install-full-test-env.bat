@echo off
REM Thin wrapper: same as repository root setup-test-environment.bat
setlocal
cd /d "%~dp0.."
call "%~dp0..\setup-test-environment.bat" %*
exit /b %ERRORLEVEL%
