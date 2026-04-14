#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  FacturIA - Comprehensive Test Suite${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Track overall success
OVERALL_SUCCESS=true

# Function to print section header
print_header() {
    echo ""
    echo -e "${BLUE}===== $1 =====${NC}"
    echo ""
}

# Function to print success
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Cleanup function
cleanup() {
    echo ""
    print_header "Cleanup"
    echo "Removing temporary files..."
    rm -f coverage-summary.json
}

trap cleanup EXIT

# Check if services are running
print_header "Pre-flight Checks"

if ! PGPASSWORD=test_password psql -h localhost -p 5433 -U test_user -d facturia_test -c "SELECT 1;" &> /dev/null; then
    print_error "PostgreSQL is not available"
    print_warning "Run: docker-compose -f .devcontainer/docker-compose.test.yml up -d postgres-test"
    exit 1
fi
print_success "PostgreSQL is available"

if ! redis-cli -h localhost -p 6380 -a test_redis_password ping &> /dev/null 2>&1; then
    print_error "Redis is not available"
    print_warning "Run: docker-compose -f .devcontainer/docker-compose.test.yml up -d redis-test"
    exit 1
fi
print_success "Redis is available"

# Backend Tests (Python/Pytest)
print_header "Backend Tests (pytest)"

cd apps/api

if pytest tests/ -v --cov=src --cov-report=html --cov-report=term --cov-report=json --cov-fail-under=80; then
    print_success "Backend tests passed"
else
    print_error "Backend tests failed"
    OVERALL_SUCCESS=false
fi

# Store backend coverage
BACKEND_COVERAGE=$(python -c "import json; print(json.load(open('coverage.json'))['totals']['percent_covered'])" 2>/dev/null || echo "0")
echo "Backend coverage: ${BACKEND_COVERAGE}%"

cd ../..

# Frontend Unit Tests (Vitest)
print_header "Frontend Unit Tests (vitest)"

cd apps/web

if pnpm test:unit --coverage --run; then
    print_success "Frontend unit tests passed"
else
    print_error "Frontend unit tests failed"
    OVERALL_SUCCESS=false
fi

# Store frontend coverage
FRONTEND_COVERAGE=$(cat coverage/coverage-summary.json 2>/dev/null | jq '.total.lines.pct' || echo "0")
echo "Frontend coverage: ${FRONTEND_COVERAGE}%"

cd ../..

# Frontend E2E Tests (Playwright)
print_header "Frontend E2E Tests (playwright)"

cd apps/web

# Check if dev server needs to be started
if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    print_warning "Dev server not running, starting it..."
    pnpm dev > /tmp/next-dev.log 2>&1 &
    DEV_SERVER_PID=$!

    # Wait for dev server
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            print_success "Dev server is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Dev server failed to start"
            cat /tmp/next-dev.log
            kill $DEV_SERVER_PID 2>/dev/null || true
            exit 1
        fi
        sleep 2
    done
fi

if pnpm test:e2e; then
    print_success "E2E tests passed"
else
    print_error "E2E tests failed"
    OVERALL_SUCCESS=false
fi

# Kill dev server if we started it
if [ ! -z "$DEV_SERVER_PID" ]; then
    kill $DEV_SERVER_PID 2>/dev/null || true
fi

cd ../..

# Type Checking
print_header "Type Checking"

# Backend type checking
cd apps/api
if mypy src --ignore-missing-imports --no-error-summary 2>/dev/null; then
    print_success "Backend type checking passed"
else
    print_warning "Backend type checking has warnings"
fi
cd ../..

# Frontend type checking
cd apps/web
if pnpm run type-check 2>/dev/null || npx tsc --noEmit; then
    print_success "Frontend type checking passed"
else
    print_warning "Frontend type checking has warnings"
fi
cd ../..

# Linting
print_header "Linting"

# Backend linting
cd apps/api
if flake8 src tests --max-line-length=100 --extend-ignore=E203,W503 2>/dev/null; then
    print_success "Backend linting passed"
else
    print_warning "Backend linting has warnings"
fi
cd ../..

# Frontend linting
cd apps/web
if pnpm run lint 2>/dev/null || npx next lint; then
    print_success "Frontend linting passed"
else
    print_warning "Frontend linting has warnings"
fi
cd ../..

# Summary
print_header "Test Summary"

echo "Backend Coverage:  ${BACKEND_COVERAGE}%"
echo "Frontend Coverage: ${FRONTEND_COVERAGE}%"
echo ""

if [ "$OVERALL_SUCCESS" = true ]; then
    print_success "All critical tests passed!"
    echo ""
    echo "📊 Coverage reports available at:"
    echo "   Backend:  apps/api/htmlcov/index.html"
    echo "   Frontend: apps/web/coverage/index.html"
    echo ""
    echo "🎭 Playwright report available at:"
    echo "   apps/web/playwright-report/index.html"
    echo ""
    exit 0
else
    print_error "Some tests failed"
    echo ""
    echo "Review the output above for details"
    exit 1
fi
