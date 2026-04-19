"""
Script para reprocesar facturas fallidas usando s3_key existente.
Llama _process_invoice_with_textract con file_content vacío → usa Textract sobre S3.
"""
import asyncio
import sys
import os
os.environ.setdefault('DOTENV_LOADED', '1')
sys.path.insert(0, '/home/edwlearn/aws-document-processing/apps/api')
os.chdir('/home/edwlearn/aws-document-processing/apps/api')

from src.services.document_processing.invoice_processor import InvoiceProcessorService

import boto3
from dotenv import load_dotenv
load_dotenv('/home/edwlearn/aws-document-processing/.env')

INVOICE_IDS = [
    # (invoice_id, s3_key, is_digital)
    ('ec3538e0-5e55-4dc4-97dc-05229e2f0b87',
     'invoices/demo-company/ec3538e0-5e55-4dc4-97dc-05229e2f0b87/45689136-2e4c-4ad9-be14-568b9b6459bc.pdf',
     True),   # PDF digital → pdfplumber
]


def download_from_s3(s3_key: str) -> bytes:
    s3 = boto3.client(
        's3',
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    )
    bucket = os.getenv('S3_DOCUMENT_BUCKET', 'facturia-documents-dev')
    obj = s3.get_object(Bucket=bucket, Key=s3_key)
    return obj['Body'].read()


async def main():
    service = InvoiceProcessorService()
    for invoice_id, s3_key, is_digital in INVOICE_IDS:
        print(f"\n→ Reprocesando {invoice_id} (digital={is_digital})")
        # Reset status first
        try:
            from src.database.connection import AsyncSessionFactory
            from src.database.models import ProcessedInvoice
            from sqlalchemy import select, update
            import uuid as _uuid
            async with AsyncSessionFactory() as session:
                await session.execute(
                    update(ProcessedInvoice)
                    .where(ProcessedInvoice.id == _uuid.UUID(invoice_id))
                    .values(status='uploaded', error_message=None)
                )
                await session.commit()
        except Exception as e:
            print(f"  Reset error: {e}")

        file_content = download_from_s3(s3_key) if is_digital else b""
        print(f"  Archivo: {len(file_content)} bytes")
        try:
            await service._process_invoice_with_textract(
                invoice_id=invoice_id,
                s3_key=s3_key,
                file_content=file_content,
                is_digital=is_digital,
                is_xml=False,
            )
            print(f"  ✓ Completado")
        except Exception as e:
            print(f"  ✗ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
