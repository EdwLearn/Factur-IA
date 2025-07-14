"""
Tests for invoice processing service
"""
import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, patch

from src.services.invoice_processor import InvoiceProcessorService
from src.models.invoice import InvoiceStatus, InvoiceType

class TestInvoiceProcessor:
    
    @pytest.fixture
    def service(self):
        return InvoiceProcessorService()
    
    @pytest.mark.asyncio
    async def test_upload_invoice(self, service):
        """Test invoice upload"""
        result = await service.upload_and_process_invoice(
            tenant_id="test-tenant",
            invoice_id="test-invoice-123",
            filename="factura.pdf",
            file_content=b"fake pdf content"
        )
        
        assert result["invoice_id"] == "test-invoice-123"
        assert result["tenant_id"] == "test-tenant"
        assert result["status"] == "uploaded"
    
    @pytest.mark.asyncio
    async def test_get_invoice_status(self, service):
        """Test getting invoice status"""
        # First upload an invoice
        await service.upload_and_process_invoice(
            tenant_id="test-tenant",
            invoice_id="test-invoice-123", 
            filename="factura.pdf",
            file_content=b"fake pdf content"
        )
        
        # Wait a bit for processing to start
        import asyncio
        await asyncio.sleep(0.1)
        
        # Get status
        invoice = await service.get_invoice_status("test-invoice-123", "test-tenant")
        
        assert invoice is not None
        assert invoice.id == "test-invoice-123"
        assert invoice.tenant_id == "test-tenant"
        assert invoice.status in [InvoiceStatus.PROCESSING, InvoiceStatus.COMPLETED]
    
    @pytest.mark.asyncio
    async def test_tenant_isolation(self, service):
        """Test that tenants can only access their own invoices"""
        # Upload invoice for tenant A
        await service.upload_and_process_invoice(
            tenant_id="tenant-a",
            invoice_id="invoice-a",
            filename="factura-a.pdf", 
            file_content=b"fake pdf content"
        )
        
        # Try to access from tenant B
        invoice = await service.get_invoice_status("invoice-a", "tenant-b")
        assert invoice is None
    
    @pytest.mark.asyncio
    async def test_list_tenant_invoices(self, service):
        """Test listing invoices for a tenant"""
        # Upload multiple invoices
        for i in range(3):
            await service.upload_and_process_invoice(
                tenant_id="test-tenant",
                invoice_id=f"invoice-{i}",
                filename=f"factura-{i}.pdf",
                file_content=b"fake pdf content"
            )
        
        # List invoices
        invoices = await service.list_tenant_invoices("test-tenant", limit=10)
        
        assert len(invoices) == 3
        assert all(inv.tenant_id == "test-tenant" for inv in invoices)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
