# Dev Containers Configuration

This directory contains Dev Container configurations for the FacturIA project, enabling isolated and reproducible development and testing environments.

## 📁 Directory Structure

```
.devcontainer/
├── devcontainer.json                    # Main development container
├── devcontainer-test.json               # Full testing environment
├── devcontainer-backend-test.json       # Backend-only testing
├── devcontainer-frontend-test.json      # Frontend-only testing
├── docker-compose.test.yml              # Testing services configuration
├── Dockerfile.test                      # Custom test runner image
├── scripts/                             # Lifecycle and utility scripts
│   ├── pre-init.sh                      # Pre-creation checks
│   ├── on-create.sh                     # Dependency installation
│   ├── update-deps.sh                   # Update dependencies
│   ├── post-start.sh                    # Health checks and info
│   ├── setup-test-env.sh                # Test environment setup
│   ├── init-localstack.sh               # LocalStack initialization
│   └── run-all-tests.sh                 # Comprehensive test runner
├── test-data/                           # Test fixtures and data
│   ├── fixtures/                        # JSON test fixtures
│   ├── sample-invoices/                 # Sample PDF/images
│   └── seed-db.sql                      # Database seed data
├── TESTING_GUIDE.md                     # Complete testing guide
└── README.md                            # This file
```

## 🚀 Quick Start

1. **Install Prerequisites**:
   - Docker Desktop
   - VS Code
   - Dev Containers extension

2. **Open Container**:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Select `Dev Containers: Reopen in Container`
   - Choose your preferred environment

3. **Run Tests**:
   ```bash
   ./.devcontainer/scripts/run-all-tests.sh
   ```

## 🎯 Available Containers

### 1. FacturIA Testing Environment
**File**: `devcontainer-test.json`

Complete testing environment with all tools and services.

**Use cases**:
- Running comprehensive test suites
- CI/CD validation
- Pre-deployment testing

**Includes**:
- Python 3.11 + Node.js 20
- pytest, vitest, playwright
- PostgreSQL, Redis, LocalStack
- Docker-in-Docker

### 2. FacturIA Backend Testing
**File**: `devcontainer-backend-test.json`

Lightweight Python/FastAPI testing environment.

**Use cases**:
- Backend development
- Python unit/integration tests
- API testing

**Includes**:
- Python 3.11
- pytest with coverage
- PostgreSQL, Redis
- No Node.js overhead

### 3. FacturIA Frontend Testing
**File**: `devcontainer-frontend-test.json`

Focused React/Next.js testing environment.

**Use cases**:
- Frontend development
- Component testing
- E2E testing

**Includes**:
- Node.js 20 + pnpm
- Vitest, Playwright
- Hot reload enabled
- No Python overhead

### 4. FacturIA Development Environment
**File**: `devcontainer.json`

Standard development container (not testing-focused).

**Use cases**:
- General development
- Quick prototyping
- Code editing

## 🔧 Configuration Files

### docker-compose.test.yml

Defines the testing infrastructure:
- `test-runner`: Main container with Docker-in-Docker
- `postgres-test`: PostgreSQL 15 test database
- `redis-test`: Redis 7 test cache
- `localstack-test`: AWS services simulation

### Dockerfile.test

Custom image for the test-runner service with:
- Python 3.11 + Node.js 20
- Testing frameworks pre-installed
- System dependencies for Playwright
- Docker CLI and docker-compose

## 📜 Lifecycle Scripts

### pre-init.sh
Runs on host machine before container creation.
- Checks Docker availability
- Verifies disk space
- Creates necessary directories

### on-create.sh
Runs once when container is first created.
- Installs Python dependencies
- Installs Node.js dependencies
- Installs Playwright browsers
- Sets up git hooks

### update-deps.sh
Manually run to update dependencies.
- Updates Python packages
- Updates Node.js packages
- Updates Playwright browsers

### post-start.sh
Runs every time the container starts.
- Waits for services to be healthy
- Tests database connections
- Displays service URLs
- Shows helpful commands

### setup-test-env.sh
Sets up the testing environment.
- Runs database migrations
- Seeds test database
- Creates S3 buckets in LocalStack
- Uploads sample documents

## 🧪 Testing Scripts

### run-all-tests.sh

Comprehensive test runner that executes:
1. Backend tests (pytest)
2. Frontend unit tests (vitest)
3. Frontend E2E tests (playwright)
4. Type checking (mypy, tsc)
5. Linting (flake8, eslint)
6. Coverage reports

**Usage**:
```bash
./.devcontainer/scripts/run-all-tests.sh
```

## 📊 Test Data

### test-data/fixtures/
JSON fixtures for programmatic testing.

**Example**:
```python
import json
with open('.devcontainer/test-data/fixtures/sample-invoice.json') as f:
    data = json.load(f)
```

### test-data/sample-invoices/
Sample PDF/image files for document processing tests.

**Usage**:
Automatically uploaded to LocalStack S3 during setup.

### test-data/seed-db.sql
Database seed data for integration tests.

**Usage**:
Automatically executed during `setup-test-env.sh`.

## 🐳 Docker-in-Docker

All testing containers support Docker-in-Docker, enabling:

- Running `docker` commands inside the container
- Executing `docker-compose.multitest.yml` for multi-environment testing
- Testing Docker-based workflows
- CI/CD pipeline simulation

**Example**:
```bash
# Inside the Dev Container
docker ps
docker-compose -f docker-compose.multitest.yml up -d
./scripts/test-multienv.sh start
```

## 🔍 Service URLs

When the test environment is running:

- **API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **PostgreSQL**: postgresql://test_user:test_password@localhost:5433/facturia_test
- **Redis**: redis://localhost:6380 (password: test_redis_password)
- **LocalStack**: http://localhost:4567

## 🛠️ Common Commands

### Inside Any Dev Container

```bash
# Backend tests
pytest apps/api/tests/ -v --cov

# Frontend unit tests
pnpm --filter web test:unit

# Frontend E2E tests
pnpm --filter web test:e2e

# All tests
./.devcontainer/scripts/run-all-tests.sh

# Multi-environment testing
./scripts/test-multienv.sh start
```

### Managing Services

```bash
# View running containers
docker-compose -f .devcontainer/docker-compose.test.yml ps

# View logs
docker-compose -f .devcontainer/docker-compose.test.yml logs -f

# Restart service
docker-compose -f .devcontainer/docker-compose.test.yml restart postgres-test

# Stop all services
docker-compose -f .devcontainer/docker-compose.test.yml down
```

## 📚 Documentation

- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)**: Complete guide for testing workflows
- **[test-data/README.md](./test-data/README.md)**: Test data documentation

## 🐛 Troubleshooting

### Container won't start
```bash
docker system prune -a
# Then rebuild container in VS Code
```

### Database connection issues
```bash
docker-compose -f .devcontainer/docker-compose.test.yml restart postgres-test
./.devcontainer/scripts/setup-test-env.sh
```

### Port conflicts
Check which process is using the port:
```bash
lsof -i :5432  # Mac/Linux
netstat -ano | findstr :5432  # Windows
```

### Slow performance
- Increase Docker Desktop resources (RAM, CPU)
- Use test markers: `pytest -m "not slow"`
- Disable coverage: `pytest --no-cov`

## 🎓 Learning Resources

- [Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Docker Documentation](https://docs.docker.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright Documentation](https://playwright.dev/)

## 🤝 Contributing

When adding new testing infrastructure:

1. Update relevant config files
2. Add scripts to `scripts/` directory
3. Document in `TESTING_GUIDE.md`
4. Test in all Dev Container variants
5. Update this README

## 📝 Notes

- First container build takes 5-10 minutes (downloads images)
- Subsequent starts take ~30 seconds (uses cache)
- Requires 8GB+ RAM and 10GB+ disk space
- All containers are isolated and don't affect host system

---

**For detailed testing instructions, see [TESTING_GUIDE.md](./TESTING_GUIDE.md)**
