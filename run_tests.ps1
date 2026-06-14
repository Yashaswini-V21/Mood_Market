# ==============================================================================
# MoodMarket Test Execution and Coverage Report Runner (PowerShell)
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=== Running Backend Linting ===" -ForegroundColor Cyan
& flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

Write-Host "=== Running Backend Type Checking ===" -ForegroundColor Cyan
try {
    & mypy . --ignore-missing-imports
} catch {
    Write-Host "Mypy type checking finished with issues" -ForegroundColor Yellow
}

Write-Host "=== Running Backend Pytest Suite & Coverage ===" -ForegroundColor Cyan
& pytest --cov=. --cov-report=term-missing --cov-report=xml:coverage.xml --cov-report=html:htmlcov

Write-Host "=== Running Frontend Jest Suite & Coverage ===" -ForegroundColor Cyan
Push-Location frontend
& npm run test -- --coverage --watchAll=false
Pop-Location

Write-Host "=== Complete Test Execution & Coverage Successfully Generated ===" -ForegroundColor Green
