#!/bin/bash

echo "🚀 Setting up PostgreSQL for Invoice SaaS..."

# Start PostgreSQL with Docker
echo "📦 Starting PostgreSQL container..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

# Install dependencies
echo "📥 Installing Python dependencies..."
pip install asyncpg databases alembic

# Run migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

# Create sample tenant
echo "👤 Creating sample tenant..."
python -c "
import asyncio
from src.database.connection import AsyncSessionFactory
from src.database.models import Tenant

async def create_sample_tenant():
    async with AsyncSessionFactory() as session:
        tenant = Tenant(
            tenant_id='empresa-test',
            company_name='Empresa Test SaaS',
            email='test@empresa.com',
            plan='freemium'
        )
        session.add(tenant)
        await session.commit()
        print('✅ Sample tenant created: empresa-test')

asyncio.run(create_sample_tenant())
"

echo "✅ Database setup complete!"
echo "🎯 Ready to test with real PostgreSQL data"
