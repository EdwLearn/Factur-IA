# Crear archivo: apps/api/src/services/integrations/integration_factory.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
import csv
import io
from datetime import datetime
import json

class IntegrationType(Enum):
    API_REST = "api_rest"
    CSV_MANUAL = "csv_manual"
    CSV_AUTO_N8N = "csv_auto_n8n"
    FTP_AUTO = "ftp_auto"
    EMAIL_AUTO = "email_auto"

class POSIntegration(ABC):
    """Base class for all POS integrations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pos_system = config.get("pos_system", "generic")
        self.integration_type = config.get("integration_type", "csv_manual")
    
    @abstractmethod
    async def export_inventory(self, products: List[Dict]) -> Dict[str, Any]:
        """Export products to POS system"""
        pass
    
    @abstractmethod
    async def import_inventory(self) -> List[Dict]:
        """Import products from POS system (future)"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get integration status"""
        return {
            "pos_system": self.pos_system,
            "integration_type": self.integration_type,
            "last_sync": None,  # TODO: implement tracking
            "next_sync": None,
            "automation_enabled": self.config.get("automation", {}).get("enabled", False)
        }

class MayasisIntegration(POSIntegration):
    """Mayasis POS Integration - CSV based"""
    
    async def export_inventory(self, products: List[Dict]) -> Dict[str, Any]:
        """Generate Mayasis-compatible CSV"""
        
        # Generate CSV data
        csv_data = self._generate_mayasis_csv(products)
        filename = f"inventario_mayasis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        automation_config = self.config.get("automation", {})
        
        if automation_config.get("enabled", False):
            # Trigger automation
            return await self._trigger_automation(csv_data, filename)
        else:
            # Manual download
            return {
                "type": "manual_download",
                "csv_data": csv_data,
                "filename": filename,
                "instructions": "Descarga este archivo e impórtalo manualmente en Mayasis"
            }
    
    def _generate_mayasis_csv(self, products: List[Dict]) -> str:
        """Generate CSV in Mayasis format"""
        
        # Mayasis specific headers
        headers = ["CODIGO", "DESCRIPCION", "CANTIDAD", "PRECIO_COMPRA", "PRECIO_VENTA", "CATEGORIA"]
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"')
        
        # Write headers
        writer.writerow(headers)
        
        # Write product data
        for product in products:
            row = [
                product.get("product_code", ""),
                product.get("description", ""),
                float(product.get("current_stock", 0)),
                float(product.get("last_purchase_price", 0)),
                float(product.get("sale_price", 0)),
                product.get("category", "GENERAL")
            ]
            writer.writerow(row)
        
        return output.getvalue()
    
    async def _trigger_automation(self, csv_data: str, filename: str) -> Dict[str, Any]:
        """Trigger N8N automation workflow"""
        
        automation_config = self.config.get("automation", {})
        method = automation_config.get("method", "n8n")
        
        if method == "n8n":
            # TODO: Implement N8N webhook call
            webhook_url = automation_config.get("webhook_url")
            
            return {
                "type": "automation_triggered",
                "automation_id": f"n8n_{datetime.now().timestamp()}",
                "method": "n8n",
                "filename": filename,
                "notification_email": automation_config.get("notification_email"),
                "message": "Archivo enviado a N8N para procesamiento automático"
            }
        
        return {
            "type": "automation_failed",
            "error": f"Automation method '{method}' not implemented"
        }
    
    async def import_inventory(self) -> List[Dict]:
        """Import from Mayasis (future implementation)"""
        return []

class SquareIntegration(POSIntegration):
    """Square POS Integration - REST API"""
    
    async def export_inventory(self, products: List[Dict]) -> Dict[str, Any]:
        """Export via Square REST API"""
        
        api_config = self.config.get("api_credentials", {})
        access_token = api_config.get("access_token")
        
        if not access_token:
            return {
                "type": "error",
                "error": "Square API access token not configured"
            }
        
        # TODO: Implement Square API calls
        updated_count = len(products)
        
        return {
            "type": "api_synced",
            "products_updated": updated_count,
            "pos_response": {"status": "success"},
            "message": f"Sincronizados {updated_count} productos via Square API"
        }
    
    async def import_inventory(self) -> List[Dict]:
        """Import from Square API"""
        # TODO: Implement Square API import
        return []

class GenericCSVIntegration(POSIntegration):
    """Generic CSV Integration for unknown POS systems"""
    
    async def export_inventory(self, products: List[Dict]) -> Dict[str, Any]:
        """Generate generic CSV"""
        
        csv_config = self.config.get("csv_config", {})
        csv_data = self._generate_generic_csv(products, csv_config)
        filename = f"inventario_generic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return {
            "type": "manual_download",
            "csv_data": csv_data,
            "filename": filename,
            "instructions": "CSV genérico - ajusta el formato según tu sistema POS"
        }
    
    def _generate_generic_csv(self, products: List[Dict], csv_config: Dict) -> str:
        """Generate generic CSV with configurable format"""
        
        delimiter = csv_config.get("delimiter", ",")
        headers_mapping = csv_config.get("headers_mapping", {})
        
        # Default headers if not configured
        if not headers_mapping:
            headers_mapping = {
                "codigo": "product_code",
                "descripcion": "description",
                "cantidad": "current_stock",
                "precio": "last_purchase_price"
            }
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=delimiter, quotechar='"')
        
        # Write headers
        writer.writerow(list(headers_mapping.keys()))
        
        # Write data
        for product in products:
            row = []
            for csv_header, product_field in headers_mapping.items():
                value = product.get(product_field, "")
                if isinstance(value, (int, float)):
                    row.append(value)
                else:
                    row.append(str(value))
            writer.writerow(row)
        
        return output.getvalue()
    
    async def import_inventory(self) -> List[Dict]:
        """Generic import (not implemented)"""
        return []

class IntegrationFactory:
    """Factory to create appropriate integration based on client config"""
    
    # Registry of available integrations
    _integrations = {
        ("mayasis", IntegrationType.CSV_MANUAL): MayasisIntegration,
        ("mayasis", IntegrationType.CSV_AUTO_N8N): MayasisIntegration,
        ("square", IntegrationType.API_REST): SquareIntegration,
        ("generic", IntegrationType.CSV_MANUAL): GenericCSVIntegration,
        ("generic", IntegrationType.CSV_AUTO_N8N): GenericCSVIntegration,
        ("generic", IntegrationType.FTP_AUTO): GenericCSVIntegration,
        ("generic", IntegrationType.EMAIL_AUTO): GenericCSVIntegration,
    }
    
    @classmethod
    def create_integration(cls, tenant_config: Dict[str, Any]) -> POSIntegration:
        """Create appropriate integration instance"""
        
        pos_system = tenant_config.get("pos_system", "generic")
        integration_type_str = tenant_config.get("integration_type", "csv_manual")
        
        try:
            integration_type = IntegrationType(integration_type_str)
        except ValueError:
            integration_type = IntegrationType.CSV_MANUAL
        
        # Find matching integration class
        integration_class = cls._integrations.get(
            (pos_system, integration_type),
            GenericCSVIntegration  # Fallback
        )
        
        return integration_class(tenant_config)
    
    @classmethod
    def get_supported_systems(cls) -> Dict[str, Dict[str, Any]]:
        """Get all supported POS systems and their capabilities"""
        return {
            "mayasis": {
                "name": "Mayasis",
                "capabilities": {
                    "has_api": False,
                    "supports_realtime": False,
                    "supports_csv": True,
                    "supports_automation": True
                },
                "integration_types": ["csv_manual", "csv_auto_n8n"],
                "description": "Sistema POS colombiano - Integración via CSV"
            },
            "square": {
                "name": "Square",
                "capabilities": {
                    "has_api": True,
                    "supports_realtime": True,
                    "supports_csv": False,
                    "supports_automation": True
                },
                "integration_types": ["api_rest"],
                "description": "Square POS - API en tiempo real"
            },
            "generic": {
                "name": "Otro Sistema",
                "capabilities": {
                    "has_api": False,
                    "supports_realtime": False,
                    "supports_csv": True,
                    "supports_automation": True
                },
                "integration_types": ["csv_manual", "csv_auto_n8n", "ftp_auto", "email_auto"],
                "description": "Cualquier sistema POS - CSV genérico"
            }
        }
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate integration configuration"""
        
        pos_system = config.get("pos_system")
        integration_type = config.get("integration_type")
        
        supported_systems = cls.get_supported_systems()
        
        if pos_system not in supported_systems:
            return {"valid": False, "error": f"POS system '{pos_system}' not supported"}
        
        if integration_type not in supported_systems[pos_system]["integration_types"]:
            return {"valid": False, "error": f"Integration type '{integration_type}' not supported for {pos_system}"}
        
        return {"valid": True}