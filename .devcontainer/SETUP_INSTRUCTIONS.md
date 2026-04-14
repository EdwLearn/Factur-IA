# Dev Containers Setup Instructions

## 🎉 Installation Complete!

Your Dev Containers testing environment has been configured. Follow these steps to start testing.

## 📋 Prerequisites Check

Before proceeding, ensure you have:

- ✅ **Docker Desktop** installed and running
- ✅ **VS Code** installed
- ✅ **Dev Containers extension** installed in VS Code
- ✅ At least **8GB RAM** available
- ✅ At least **10GB disk space** free

## 🚀 First Time Setup

### Step 1: Verify Docker is Running

```bash
docker info
```

If this fails, start Docker Desktop and wait for it to be ready.

### Step 2: Open in Dev Container

1. Open VS Code in the project directory:
   ```bash
   code .
   ```

2. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)

3. Type: `Dev Containers: Reopen in Container`

4. Select one of the available containers:
   - **FacturIA Testing Environment** (recommended for first time)
   - FacturIA Backend Testing
   - FacturIA Frontend Testing
   - FacturIA Development Environment

5. Wait for the container to build (5-10 minutes first time)

### Step 3: Verify Installation

Once inside the container, run:

```bash
# Check services are running
docker-compose -f .devcontainer/docker-compose.test.yml ps

# Setup test environment
./.devcontainer/scripts/setup-test-env.sh

# Check everything is ready
./.devcontainer/scripts/post-start.sh
```

### Step 4: Run Your First Tests

```bash
# Run all tests
./.devcontainer/scripts/run-all-tests.sh
```

## 📖 What Was Created

### Configuration Files

```
.devcontainer/
├── devcontainer.json                    ✅ Main dev container
├── devcontainer-test.json               ✅ Full testing environment
├── devcontainer-backend-test.json       ✅ Backend-only testing
├── devcontainer-frontend-test.json      ✅ Frontend-only testing
├── docker-compose.test.yml              ✅ Testing services
├── Dockerfile.test                      ✅ Custom test image
```

### Scripts (All executable)

```
.devcontainer/scripts/
├── pre-init.sh                          ✅ Pre-creation checks
├── on-create.sh                         ✅ Install dependencies
├── update-deps.sh                       ✅ Update dependencies
├── post-start.sh                        ✅ Health checks
├── setup-test-env.sh                    ✅ Setup test environment
├── init-localstack.sh                   ✅ Initialize LocalStack
└── run-all-tests.sh                     ✅ Run all tests
```

### Test Data

```
.devcontainer/test-data/
├── fixtures/
│   └── sample-invoice.json              ✅ Test fixtures
├── sample-invoices/
│   └── .gitkeep                         ✅ Directory placeholder
├── seed-db.sql                          ✅ Database seed data
└── README.md                            ✅ Test data docs
```

### Documentation

```
.devcontainer/
├── README.md                            ✅ Overview
├── TESTING_GUIDE.md                     ✅ Complete guide
└── SETUP_INSTRUCTIONS.md                ✅ This file
```

## 🎯 Testing Workflows

### Quick Test (2-3 minutes)

Run basic tests to verify everything works:

```bash
# Backend tests only
pytest apps/api/tests/unit -v

# Frontend tests only
pnpm --filter web test:unit
```

### Full Test Suite (10-15 minutes)

Run comprehensive tests:

```bash
./.devcontainer/scripts/run-all-tests.sh
```

This includes:
- Backend unit & integration tests
- Frontend unit tests
- E2E tests with Playwright
- Type checking
- Linting
- Coverage reports

### Multi-Environment Testing

Simulate testing from different OS clients:

```bash
# Start multi-environment setup
./scripts/test-multienv.sh start

# Test from simulated Windows client
./scripts/test-multienv.sh test-client windows

# Test from simulated Mac client
./scripts/test-multienv.sh test-client mac

# Test from simulated Linux client
./scripts/test-multienv.sh test-client linux

# Cleanup
./scripts/test-multienv.sh clean
```

## 🔧 Available Commands

### Inside Dev Container

```bash
# View service status
docker-compose -f .devcontainer/docker-compose.test.yml ps

# View logs
docker-compose -f .devcontainer/docker-compose.test.yml logs -f

# Restart a service
docker-compose -f .devcontainer/docker-compose.test.yml restart postgres-test

# Connect to PostgreSQL
PGPASSWORD=test_password psql -h localhost -p 5433 -U test_user -d facturia_test

# Connect to Redis
redis-cli -h localhost -p 6380 -a test_redis_password

# Check LocalStack health
curl http://localhost:4567/_localstack/health
```

### Testing Shortcuts

```bash
# Backend
pytest apps/api/tests/ -v                    # All tests
pytest apps/api/tests/ -m unit               # Unit tests only
pytest apps/api/tests/ -m integration        # Integration tests only
pytest apps/api/tests/ --cov                 # With coverage

# Frontend
pnpm --filter web test:unit                  # Unit tests
pnpm --filter web test:watch                 # Watch mode
pnpm --filter web test:e2e                   # E2E tests
pnpm --filter web test:e2e:ui                # E2E with UI

# Type checking
cd apps/api && mypy src                      # Backend
cd apps/web && npx tsc --noEmit              # Frontend

# Linting
cd apps/api && flake8 src                    # Backend
cd apps/web && pnpm run lint                 # Frontend
```

## 🐛 Troubleshooting

### Issue: Container Won't Start

**Solution**:
```bash
# Clean Docker resources
docker system prune -a

# Rebuild container
# In VS Code: Ctrl+Shift+P → "Dev Containers: Rebuild Container"
```

### Issue: Port Already in Use

**Solution**:
```bash
# Find process using port
lsof -i :5432  # Mac/Linux
netstat -ano | findstr :5432  # Windows

# Kill process or change port in docker-compose.test.yml
```

### Issue: Tests Fail - Database Connection

**Solution**:
```bash
# Check PostgreSQL is running
docker-compose -f .devcontainer/docker-compose.test.yml ps postgres-test

# Restart PostgreSQL
docker-compose -f .devcontainer/docker-compose.test.yml restart postgres-test

# Re-setup environment
./.devcontainer/scripts/setup-test-env.sh
```

### Issue: Slow Performance

**Solutions**:
1. Increase Docker Desktop resources:
   - Docker Desktop → Settings → Resources
   - RAM: 8GB minimum, 16GB recommended
   - CPUs: 4+ cores

2. Run faster tests:
   ```bash
   pytest -m "not slow"  # Skip slow tests
   pytest --no-cov       # Disable coverage
   ```

### Issue: Playwright Browsers Missing

**Solution**:
```bash
cd apps/web
pnpm exec playwright install --with-deps chromium
```

### Issue: LocalStack Not Working

**Solution**:
```bash
# Restart LocalStack
docker-compose -f .devcontainer/docker-compose.test.yml restart localstack-test

# Check health
curl http://localhost:4567/_localstack/health

# Re-initialize
./.devcontainer/scripts/init-localstack.sh
```

## 📚 Next Steps

1. **Read the Testing Guide**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
2. **Explore Test Data**: [test-data/README.md](./test-data/README.md)
3. **Write Your Tests**: Add tests to `apps/api/tests/` or `apps/web/tests/`
4. **Run Tests Regularly**: Use the test scripts frequently during development

## 🎓 Learning Path

### Beginner
1. Open "FacturIA Testing Environment" container
2. Run `./.devcontainer/scripts/run-all-tests.sh`
3. Explore generated coverage reports
4. Modify an existing test and re-run

### Intermediate
1. Switch between different Dev Containers
2. Run specific test suites (unit, integration, e2e)
3. Use Docker-in-Docker for multi-environment testing
4. Debug tests with breakpoints in VS Code

### Advanced
1. Create custom test fixtures in `test-data/fixtures/`
2. Add new test markers in `pytest.ini`
3. Configure CI/CD to use these containers
4. Optimize test performance and coverage

## 🤝 Getting Help

- **Documentation**: Start with [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- **Troubleshooting**: Check the section above
- **Logs**: Always check container logs for errors
- **Team**: Ask your team for help
- **Issues**: Report bugs in GitHub

## ✅ Verification Checklist

Before considering setup complete, verify:

- [ ] Dev Container opens without errors
- [ ] All scripts are executable (`ls -la .devcontainer/scripts/`)
- [ ] PostgreSQL is accessible (port 5433)
- [ ] Redis is accessible (port 6380)
- [ ] LocalStack is accessible (port 4567)
- [ ] Backend tests run successfully
- [ ] Frontend tests run successfully
- [ ] Test coverage reports are generated
- [ ] Docker-in-Docker works (`docker ps`)

## 🎉 Success!

If all checks pass, your Dev Container testing environment is ready!

Start writing and running tests with confidence in an isolated, reproducible environment.

---

**Happy Testing! 🚀**

For detailed guides and workflows, see:
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Complete testing documentation
- [README.md](./README.md) - Configuration overview
- [test-data/README.md](./test-data/README.md) - Test data documentation
