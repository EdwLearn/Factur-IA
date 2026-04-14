#!/bin/bash
set -e

echo "🚀 Post-start checks..."

# Wait for services to be healthy
wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=1

    echo "⏳ Waiting for $service to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f .devcontainer/docker-compose.test.yml ps | grep "$service" | grep -q "healthy\|running"; then
            echo "✅ $service is ready"
            return 0
        fi

        echo "   Attempt $attempt/$max_attempts - $service not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "⚠️  $service did not become ready in time"
    return 1
}

# Check PostgreSQL
if docker-compose -f .devcontainer/docker-compose.test.yml ps | grep -q postgres-test; then
    wait_for_service "postgres-test"

    # Test database connection
    if PGPASSWORD=test_password psql -h localhost -p 5433 -U test_user -d facturia_test -c "SELECT 1;" &> /dev/null; then
        echo "✅ PostgreSQL connection successful"
    else
        echo "⚠️  PostgreSQL connection failed"
    fi
fi

# Check Redis
if docker-compose -f .devcontainer/docker-compose.test.yml ps | grep -q redis-test; then
    wait_for_service "redis-test"

    # Test Redis connection
    if redis-cli -h localhost -p 6380 -a test_redis_password ping &> /dev/null; then
        echo "✅ Redis connection successful"
    else
        echo "⚠️  Redis connection failed"
    fi
fi

# Check LocalStack
if docker-compose -f .devcontainer/docker-compose.test.yml ps | grep -q localstack-test; then
    wait_for_service "localstack-test"

    # Test LocalStack connection
    if curl -s http://localhost:4567/_localstack/health | grep -q '"s3": "available"'; then
        echo "✅ LocalStack S3 is available"
    else
        echo "⚠️  LocalStack S3 not available yet"
    fi
fi

# Display service URLs
echo ""
echo "📋 Available services:"
echo "   🗄️  PostgreSQL:  postgresql://test_user:test_password@localhost:5433/facturia_test"
echo "   🔴 Redis:       redis://localhost:6380 (password: test_redis_password)"
echo "   ☁️  LocalStack:  http://localhost:4567"
echo "   🔧 Docker:      /var/run/docker.sock"
echo ""

# Display helpful commands
echo "💡 Helpful commands:"
echo "   Run all tests:              ./.devcontainer/scripts/run-all-tests.sh"
echo "   Backend tests:              pytest apps/api/tests/ -v"
echo "   Frontend unit tests:        pnpm --filter web test:unit"
echo "   Frontend e2e tests:         pnpm --filter web test:e2e"
echo "   Multi-env testing:          ./scripts/test-multienv.sh start"
echo "   View service logs:          docker-compose -f .devcontainer/docker-compose.test.yml logs -f"
echo ""

echo "✅ Post-start checks completed"
