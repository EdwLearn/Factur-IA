"""
StorageCleanupService — elimina archivos S3 de facturas cuyo plan
de almacenamiento ha expirado.

Corre diariamente desde el lifespan de FastAPI. Para cada tenant:
  - Lee su plan y obtiene storage_days de PLAN_LIMITS.
  - Pro (storage_days=None) → skip, almacenamiento ilimitado.
  - Los demás → borra S3 y marca storage_expired=True en DB.
"""
import logging
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import select, update

from ...config.plans import PLAN_LIMITS
from ...core.config import settings
from ...database.connection import AsyncSessionFactory
from ...database.models import ProcessedInvoice, Tenant

logger = logging.getLogger(__name__)


class StorageCleanupService:

    async def cleanup_expired_invoices(self) -> None:
        """
        Corre diariamente. Para cada tenant:
        1. Lee su plan actual.
        2. Obtiene storage_days del PLAN_LIMITS.
        3. Si storage_days es None → skip (pro, ilimitado).
        4. Busca processed_invoices donde:
           - tenant_id = tenant.tenant_id
           - upload_timestamp < ahora - storage_days días
           - s3_key no es None
           - storage_expired = False  (no procesadas ya)
        5. Para cada factura encontrada:
           a. Elimina el archivo de S3 usando s3_key.
           b. Setea s3_key = None en la DB.
           c. Setea storage_expired = True en la DB.
        6. Loguea cuántos archivos se eliminaron por tenant.
        """
        logger.info("StorageCleanupService: iniciando limpieza diaria de S3...")

        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(Tenant).where(Tenant.is_active == True)  # noqa: E712
            )
            tenants = result.scalars().all()

        for tenant in tenants:
            plan_name = tenant.plan or "freemium"
            limits = PLAN_LIMITS.get(plan_name, PLAN_LIMITS["freemium"])
            storage_days = limits.get("storage_days")

            if storage_days is None:
                # Pro — almacenamiento ilimitado, no tocar.
                continue

            cutoff = datetime.now(tz=timezone.utc) - timedelta(days=storage_days)
            deleted_count = 0

            async with AsyncSessionFactory() as session:
                result = await session.execute(
                    select(ProcessedInvoice).where(
                        ProcessedInvoice.tenant_id == tenant.tenant_id,
                        ProcessedInvoice.upload_timestamp < cutoff,
                        ProcessedInvoice.s3_key.isnot(None),
                        ProcessedInvoice.storage_expired == False,  # noqa: E712
                    )
                )
                invoices = result.scalars().all()

                for invoice in invoices:
                    success = await self._delete_from_s3(invoice.s3_key)
                    await session.execute(
                        update(ProcessedInvoice)
                        .where(ProcessedInvoice.id == invoice.id)
                        .values(
                            s3_key=None if success else invoice.s3_key,
                            storage_expired=True,
                        )
                    )
                    if success:
                        deleted_count += 1

                await session.commit()

            logger.info(
                "StorageCleanupService: tenant=%s plan=%s storage_days=%d "
                "facturas_expiradas=%d archivos_eliminados=%d",
                tenant.tenant_id,
                plan_name,
                storage_days,
                len(invoices),
                deleted_count,
            )

        logger.info("StorageCleanupService: limpieza completada.")

    async def _delete_from_s3(self, s3_key: str) -> bool:
        """
        Elimina un archivo de S3.
        Retorna True si fue exitoso, False si falló.
        Nunca lanza excepción — loguea el error y sigue.
        """
        try:
            s3_client = boto3.client(
                "s3",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            s3_client.delete_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
            )
            logger.debug("S3 delete OK: %s", s3_key)
            return True
        except ClientError as exc:
            logger.error("S3 delete FAILED for key=%s: %s", s3_key, exc)
            return False
        except Exception as exc:
            logger.error("S3 delete unexpected error for key=%s: %s", s3_key, exc)
            return False
