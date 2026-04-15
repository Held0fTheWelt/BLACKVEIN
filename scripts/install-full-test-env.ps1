# Full Python test environment for ``python tests/run_tests.py`` (all suites).
# Delegates to repository root ``setup-test-environment.bat`` (Windows) or call
# ``setup-test-environment.sh`` from Git Bash / WSL.
#
# Usage (from repository root):
#   .\scripts\install-full-test-env.ps1
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Batch = Join-Path $Root "setup-test-environment.bat"
if (-not (Test-Path $Batch)) {
    Write-Error "Expected $Batch"
}
& cmd /c "`"$Batch`""
exit $LASTEXITCODE
