# Minimal, CI-identical install for ai_stack tests (LangChain / LangGraph / GoC regression).
# Usage (from repository root, PowerShell):
#   .\scripts\install-ai-stack-test-env.ps1
#
# Mirrors: .github/workflows/ai-stack-tests.yml
param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Using: " -NoNewline
& $Python --version
Write-Host "Repo:  $Root"

& $Python -m pip install --upgrade pip
& $Python -m pip install -e "./story_runtime_core"
& $Python -m pip install -e "./ai_stack[test]"

Write-Host "Verifying heavy stack (same imports as langgraph_runtime)..."
& $Python -c "import langchain_core, langgraph; import ai_stack.langgraph_runtime; print('OK: langchain_core, langgraph, ai_stack.langgraph_runtime')"

Write-Host ""
Write-Host "Run tests:"
Write-Host "  `$env:PYTHONPATH='$Root'; $Python -m pytest ai_stack/tests -q --tb=short"
