#!/bin/bash
set -e

echo "🔧 Setting up test environment..."

# Wait for database to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if PGPASSWORD=test_password psql -h localhost -p 5433 -U test_user -d facturia_test -c "SELECT 1;" &> /dev/null; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL did not become ready in time"
        exit 1
    fi
    sleep 2
done

# Run database migrations (if using Alembic)
if [ -f "apps/api/alembic.ini" ]; then
    echo "🔄 Running database migrations..."
    cd apps/api && alembic upgrade head && cd ../..
    echo "✅ Migrations completed"
fi

# Seed test database with sample data
if [ -f ".devcontainer/test-data/seed-db.sql" ]; then
    echo "🌱 Seeding test database..."
    PGPASSWORD=test_password psql -h localhost -p 5433 -U test_user -d facturia_test -f .devcontainer/test-data/seed-db.sql
    echo "✅ Database seeded"
fi

# Setup LocalStack S3 buckets
echo "☁️  Configuring LocalStack..."
for i in {1..30}; do
    if curl -s http://localhost:4567/_localstack/health | grep -q "running"; then
        echo "✅ LocalStack is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  LocalStack did not become ready in time"
    fi
    sleep 2
done

# Create S3 bucket
echo "📦 Creating S3 bucket..."
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test aws --endpoint-url=http://localhost:4567 s3 mb s3://facturia-test-documents 2>/dev/null || echo "Bucket already exists"
echo "✅ S3 bucket created"

# Upload sample documents to S3
if [ -d ".devcontainer/test-data/sample-invoices" ]; then
    echo "📄 Uploading sample invoices to S3..."
    AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test aws --endpoint-url=http://localhost:4567 s3 sync .devcontainer/test-data/sample-invoices s3://facturia-test-documents/samples/
    echo "✅ Sample invoices uploaded"
fi

# Setup Redis test data (if needed)
echo "🔴 Configuring Redis..."
if redis-cli -h localhost -p 6380 -a test_redis_password ping &> /dev/null; then
    echo "✅ Redis is ready"
else
    echo "⚠️  Redis connection failed"
fi

echo "✅ Test environment setup completed successfully"
