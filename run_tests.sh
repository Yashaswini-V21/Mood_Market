#!/bin/bash
# ==============================================================================
# MoodMarket Test Execution and Coverage Report Runner
# ==============================================================================

set -e

echo "=== Running Backend Linting ==="
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

echo "=== Running Backend Type Checking ==="
mypy . --ignore-missing-imports || true

echo "=== Running Backend Pytest Suite & Coverage ==="
pytest --cov=. --cov-report=term-missing --cov-report=xml:coverage.xml --cov-report=html:htmlcov

echo "=== Running Frontend Jest Suite & Coverage ==="
cd frontend
npm run test -- --coverage --watchAll=false
cd ..

echo "=== Complete Test Execution & Coverage Successfully Generated ==="
