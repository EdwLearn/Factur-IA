# FacturIA Dev Containers Testing Guide

Complete guide for using Dev Containers to test the FacturIA application in isolated Docker environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Available Dev Containers](#available-dev-containers)
4. [Testing Workflows](#testing-workflows)
5. [Multi-Environment Testing](#multi-environment-testing)
6. [Debugging](#debugging)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## Prerequisites

### Required Software

- **Docker Desktop** (version 20.10 or higher)
  - [Download for Windows](https://docs.docker.com/desktop/install/windows-install/)
  - [Download for Mac](https://docs.docker.com/desktop/install/mac-install/)
  - [Download for Linux](https://docs.docker.com/desktop/install/linux-install/)

- **Visual Studio Code** (version 1.75 or higher)
  - [Download VS Code](https://code.visualstudio.com/)

- **Dev Containers Extension** for VS Code
  - Install from: [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### System Requirements

- **RAM**: Minimum 8GB (16GB recommended)
- **Disk Space**: At least 10GB free
- **CPU**: Multi-core processor (4+ cores recommended)

### First-Time Setup

1. Start Docker Desktop
2. Clone the repository:
   ```bash
   git clone <repository-url>
   cd aws-document-processing
   ```
3. Open VS Code:
   ```bash
   code .
   ```

---

## Quick Start

### Opening a Dev Container

1. **Open Command Palette**: `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)

2. **Select**: `Dev Containers: Reopen in Container`

3. **Choose a container**:
   - `FacturIA Testing Environment` - Full testing environment (recommended)
   - `FacturIA Backend Testing` - Backend-only testing
   - `FacturIA Frontend Testing` - Frontend-only testing
   - `FacturIA Development Environment` - Standard development

4. **Wait** for the container to build (5-10 minutes first time, ~30 seconds after)

5. **Start testing** once VS Code reopens in the container

### Running Your First Tests

Once inside the Dev Container:

```bash
# Run all tests
./.devcontainer/scripts/run-all-tests.sh

# Or run specific test suites
pytest apps/api/tests/ -v                    # Backend tests
pnpm --filter web test:unit                  # Frontend unit tests
pnpm --filter web test:e2e                   # Frontend E2E tests
```

---

## Available Dev Containers

### 1. FacturIA Testing Environment (Recommended)

**File**: `.devcontainer/devcontainer-test.json`

**Best for**: Comprehensive testing, CI/CD validation, pre-deployment checks

**Features**:
- Full Python + Node.js environment
- Docker-in-Docker enabled
- All testing frameworks (pytest, vitest, playwright)
- LocalStack for AWS simulation
- PostgreSQL and Redis test databases

**Use when**: You need to run the complete test suite

### 2. FacturIA Backend Testing

**File**: `.devcontainer/devcontainer-backend-test.json`

**Best for**: Python/FastAPI development and testing

**Features**:
- Python 3.11 with pytest
- PostgreSQL test database
- Redis test cache
- AWS LocalStack
- No Node.js overhead

**Use when**: Working exclusively on backend code

### 3. FacturIA Frontend Testing

**File**: `.devcontainer/devcontainer-frontend-test.json`

**Best for**: React/Next.js development and testing

**Features**:
- Node.js 20 with pnpm
- Vitest and Playwright
- Hot reload enabled
- No Python overhead

**Use when**: Working exclusively on frontend code

### 4. FacturIA Development Environment

**File**: `.devcontainer/devcontainer.json`

**Best for**: General development (not focused on testing)

**Features**:
- Minimal setup for quick development
- All services available
- Lighter resource usage

**Use when**: Writing features without running full test suites

---

## Testing Workflows

### Backend Testing Workflow

```bash
# Enter backend directory
cd apps/api

# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test markers
pytest tests/ -m unit                 # Only unit tests
pytest tests/ -m integration          # Only integration tests
pytest tests/ -m "not slow"           # Skip slow tests

# Run specific test file
pytest tests/unit/test_invoice_processing.py -v

# Run with debugging
pytest tests/ -v --pdb                # Drop into debugger on failure

# Check coverage report
open apps/api/htmlcov/index.html      # Mac
xdg-open apps/api/htmlcov/index.html  # Linux
```

### Frontend Unit Testing Workflow

```bash
# Enter frontend directory
cd apps/web

# Run all unit tests
pnpm test:unit

# Run in watch mode (development)
pnpm test:watch

# Run with coverage
pnpm test:unit --coverage

# Run specific test file
pnpm vitest run tests/unit/components/InvoiceCard.test.tsx

# Update snapshots
pnpm test:unit -u

# View coverage report
open coverage/index.html
```

### Frontend E2E Testing Workflow

```bash
cd apps/web

# Run E2E tests (headless)
pnpm test:e2e

# Run with UI mode (interactive)
pnpm test:e2e:ui

# Run specific test
pnpm playwright test tests/e2e/invoice-upload.spec.ts

# Debug mode (step through)
pnpm playwright test --debug

# View test report
pnpm playwright show-report
```

### Full Test Suite

```bash
# From repository root
./.devcontainer/scripts/run-all-tests.sh

# This runs:
# 1. Backend tests (pytest)
# 2. Frontend unit tests (vitest)
# 3. Frontend E2E tests (playwright)
# 4. Type checking (mypy, tsc)
# 5. Linting (flake8, eslint)
# 6. Coverage reports
```

---

## Multi-Environment Testing

Test your application as if it's running on different machines/operating systems.

### Starting Multi-Environment Tests

```bash
# Start all test environments (Windows, Mac, Linux clients)
./scripts/test-multienv.sh start

# Check status
./scripts/test-multienv.sh status

# View logs
./scripts/test-multienv.sh logs test-server
./scripts/test-multienv.sh logs test-client-windows
```

### Testing from Specific Clients

```bash
# Test from simulated Windows client
./scripts/test-multienv.sh test-client windows

# Test from simulated Mac client
./scripts/test-multienv.sh test-client mac

# Test from simulated Linux client
./scripts/test-multienv.sh test-client linux
```

### Network Testing

```bash
# Inspect network configuration
./scripts/test-multienv.sh network

# Test connectivity between services
./scripts/test-multienv.sh connectivity
```

### Cleanup

```bash
# Stop all containers
./scripts/test-multienv.sh stop

# Remove all containers and volumes
./scripts/test-multienv.sh clean
```

---

## Debugging

### Backend Debugging (Python)

1. **Set breakpoints** in VS Code (click left of line number)

2. **Launch debugger**:
   - Open "Run and Debug" panel (`Ctrl+Shift+D`)
   - Select "Python: FastAPI"
   - Press F5

3. **Attach to running tests**:
   ```python
   # Add to test file
   import ipdb; ipdb.set_trace()
   ```

### Frontend Debugging (TypeScript)

1. **Browser DevTools**:
   ```bash
   pnpm --filter web dev
   # Open http://localhost:3000
   # Use browser DevTools (F12)
   ```

2. **VS Code debugger**:
   - Set breakpoints in `.tsx` files
   - Launch "Next.js: debug full stack"
   - Press F5

3. **Playwright UI mode**:
   ```bash
   pnpm --filter web test:e2e:ui
   # Interactive test execution with time-travel debugging
   ```

### Database Debugging

```bash
# Connect to test database
PGPASSWORD=test_password psql -h localhost -p 5433 -U test_user -d facturia_test

# Inspect tables
\dt

# Query data
SELECT * FROM invoices;

# Exit
\q
```

### Redis Debugging

```bash
# Connect to Redis
redis-cli -h localhost -p 6380 -a test_redis_password

# List all keys
KEYS *

# Get value
GET key_name

# Exit
exit
```

### Docker Debugging

```bash
# List all containers
docker ps -a

# View container logs
docker logs facturia_test_runner
docker logs facturia_postgres_test

# Execute command in container
docker exec -it facturia_test_runner bash

# Inspect container
docker inspect facturia_test_runner
```

---

## Troubleshooting

### Container Won't Start

**Problem**: Dev Container fails to start or build

**Solutions**:
1. Check Docker is running:
   ```bash
   docker info
   ```

2. Clean Docker resources:
   ```bash
   docker system prune -a
   ```

3. Rebuild container:
   - Command Palette → `Dev Containers: Rebuild Container`

4. Check disk space:
   ```bash
   df -h
   ```

### Tests Fail with Database Errors

**Problem**: `Connection refused` or `database does not exist`

**Solutions**:
1. Check PostgreSQL is running:
   ```bash
   docker-compose -f .devcontainer/docker-compose.test.yml ps
   ```

2. Restart database:
   ```bash
   docker-compose -f .devcontainer/docker-compose.test.yml restart postgres-test
   ```

3. Re-initialize:
   ```bash
   ./.devcontainer/scripts/setup-test-env.sh
   ```

### Port Already in Use

**Problem**: `Port 5432 is already allocated`

**Solutions**:
1. Find process using port:
   ```bash
   lsof -i :5432  # Mac/Linux
   netstat -ano | findstr :5432  # Windows
   ```

2. Stop conflicting service or change port in `docker-compose.test.yml`

### Slow Performance

**Problem**: Tests run very slowly

**Solutions**:
1. Increase Docker resources:
   - Docker Desktop → Settings → Resources
   - Increase RAM to 8GB+
   - Increase CPU to 4+ cores

2. Use test markers to run faster tests:
   ```bash
   pytest -m "not slow"
   ```

3. Disable coverage:
   ```bash
   pytest tests/ --no-cov
   ```

### LocalStack Issues

**Problem**: S3 or Textract not working

**Solutions**:
1. Check LocalStack health:
   ```bash
   curl http://localhost:4567/_localstack/health
   ```

2. Restart LocalStack:
   ```bash
   docker-compose -f .devcontainer/docker-compose.test.yml restart localstack-test
   ```

3. Re-initialize:
   ```bash
   ./.devcontainer/scripts/init-localstack.sh
   ```

### Playwright Browser Issues

**Problem**: `Browser executable not found`

**Solutions**:
1. Install browsers:
   ```bash
   cd apps/web && pnpm exec playwright install --with-deps
   ```

2. Or reinstall dependencies:
   ```bash
   ./.devcontainer/scripts/update-deps.sh
   ```

---

## Best Practices

### Test Organization

- **Unit tests**: Fast, isolated, no external dependencies
- **Integration tests**: Test with database, Redis, external APIs
- **E2E tests**: Test complete user flows in browser

### Running Tests Efficiently

1. **During development**: Run unit tests in watch mode
   ```bash
   pytest tests/unit --watch
   pnpm test:watch
   ```

2. **Before committing**: Run affected tests
   ```bash
   pytest tests/unit tests/integration
   ```

3. **Before pushing**: Run full suite
   ```bash
   ./.devcontainer/scripts/run-all-tests.sh
   ```

4. **Pre-deployment**: Run multi-environment tests
   ```bash
   ./scripts/test-multienv.sh start
   ./scripts/test-multienv.sh test-client windows
   ./scripts/test-multienv.sh test-client mac
   ./scripts/test-multienv.sh test-client linux
   ```

### Coverage Goals

- **Backend**: Maintain 80%+ coverage
- **Frontend**: Maintain 80%+ coverage
- Focus on critical paths (authentication, invoice processing, payments)
- Don't obsess over 100% - focus on meaningful tests

### Resource Management

- **Stop containers** when not testing:
  ```bash
  docker-compose -f .devcontainer/docker-compose.test.yml down
  ```

- **Clean up volumes** periodically:
  ```bash
  docker volume prune
  ```

- **Use specific containers**: Use backend-only or frontend-only containers when possible

### Git Workflow

1. Create feature branch
2. Open appropriate Dev Container
3. Write code + tests
4. Run test suite
5. Commit with passing tests
6. Push and create PR

---

## Additional Resources

- [Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Pytest Documentation](https://docs.pytest.org/)
- [Vitest Documentation](https://vitest.dev/)
- [Playwright Documentation](https://playwright.dev/)
- [LocalStack Documentation](https://docs.localstack.cloud/)

---

## Getting Help

- Check this guide first
- Review troubleshooting section
- Check container logs: `docker-compose logs -f`
- Ask the team for help
- Report issues in GitHub

---

**Happy Testing! 🎉**
