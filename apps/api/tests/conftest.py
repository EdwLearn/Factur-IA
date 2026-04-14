"""
Pytest configuration and shared fixtures.
"""

import asyncio
import pytest
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from moto import mock_s3, mock_textract
import boto3

from src.core.config import Settings, get_settings
from src.database.connection import Base, get_db
from src.api.main import app


# Test settings
@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Get test environment settings."""
    return Settings(
        environment="test",
        db_name="facturia_test",
        db_host="localhost",
        db_port=5433,
        redis_port=6380,
        aws_endpoint_url="http://localhost:4566",
        s3_document_bucket="facturia-test-documents",
        log_level="DEBUG",
    )


# Override settings
@pytest.fixture(autouse=True)
def override_get_settings(test_settings):
    """Override settings for all tests."""
    app.dependency_overrides[get_settings] = lambda: test_settings


# Database fixtures
@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    # Use in-memory SQLite for faster tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session) -> TestClient:
    """Create FastAPI test client."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


# AWS mocks
@pytest.fixture(scope="function")
def aws_credentials():
    """Mock AWS credentials for moto."""
    import os
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    """Create mocked S3 client."""
    with mock_s3():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="facturia-test-documents")
        yield s3


@pytest.fixture(scope="function")
def textract_client(aws_credentials):
    """Create mocked Textract client."""
    with mock_textract():
        yield boto3.client("textract", region_name="us-east-1")


@pytest.fixture(scope="function")
def mock_aws_services(s3_client, textract_client):
    """Mock all AWS services together."""
    return {
        "s3": s3_client,
        "textract": textract_client,
    }


# Async fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Sample data fixtures
@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing."""
    return {
        "tenant_id": "test-tenant",
        "invoice_number": "INV-001",
        "supplier_name": "Test Supplier",
        "total_amount": 100000,
        "status": "uploaded",
        "pricing_status": "pending",
    }


@pytest.fixture
def sample_line_item_data():
    """Sample line item data for testing."""
    return {
        "product_code": "TEST001",
        "description": "Test Product",
        "quantity": 10,
        "unit_price": 10000,
        "total_price": 100000,
        "is_priced": False,
    }


# Helper functions
@pytest.fixture
def create_test_invoice(db_session):
    """Factory for creating test invoices."""
    from src.models.database.invoice import ProcessedInvoice

    def _create(**kwargs):
        defaults = {
            "tenant_id": "test-tenant",
            "invoice_number": "INV-TEST",
            "supplier_name": "Test Supplier",
            "total_amount": 100000,
            "status": "uploaded",
            "pricing_status": "pending",
        }
        defaults.update(kwargs)
        invoice = ProcessedInvoice(**defaults)
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)
        return invoice

    return _create


@pytest.fixture
def create_test_line_item(db_session):
    """Factory for creating test line items."""
    from src.models.database.invoice import InvoiceLineItem

    def _create(invoice_id, **kwargs):
        defaults = {
            "invoice_id": invoice_id,
            "product_code": "TEST001",
            "description": "Test Product",
            "quantity": 1,
            "unit_price": 10000,
            "total_price": 10000,
            "is_priced": False,
        }
        defaults.update(kwargs)
        item = InvoiceLineItem(**defaults)
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        return item

    return _create
