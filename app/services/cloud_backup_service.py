"""Snapshot cifrado del usuario. S3 si hay llaves; si no, copia firmada en el almacén híbrido."""

import hashlib
import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import cifrar
from app.models.education import ProgresoEducativo
from app.models.goal import MetaAhorro
from app.models.transaction import Transaccion
from app.models.user import Usuario
from app.services.account_service import get_cuenta_usuario
from app.services.ai_store import guardar_habito


def _bucket() -> str:
    return settings.aws_s3_bucket or settings.aws_s3_kyc_bucket


def _s3_listo() -> bool:
    return bool(_bucket() and settings.aws_access_key_id and settings.aws_secret_access_key)


async def respaldar(db: AsyncSession, usuario: Usuario) -> dict:
    cuenta = await get_cuenta_usuario(db, usuario)
    movimientos = (
        await db.scalars(
            select(Transaccion)
            .where(Transaccion.iniciada_por_usuario_id == usuario.id)
            .order_by(Transaccion.created_at.desc())
            .limit(50)
        )
    ).all()
    metas = (await db.scalars(select(MetaAhorro).where(MetaAhorro.cuenta_id == cuenta.id))).all()
    insignias = (
        await db.scalars(select(ProgresoEducativo).where(ProgresoEducativo.usuario_id == usuario.id))
    ).all()
    snapshot = {
        "usuario": {"id": str(usuario.id), "email": usuario.email, "rol": usuario.rol, "moneda": usuario.moneda_preferida},
        "cuenta": {"id": str(cuenta.id), "saldo": f"{Decimal(cuenta.saldo):.2f}", "moneda": cuenta.moneda},
        "movimientos": [
            {"id": str(tx.id), "tipo": tx.tipo, "monto": f"{Decimal(tx.monto):.2f}", "categoria": tx.categoria}
            for tx in movimientos
        ],
        "metas": [{"nombre": meta.nombre, "actual": f"{Decimal(meta.monto_actual):.2f}"} for meta in metas],
        "insignias": [item.insignia for item in insignias],
    }
    canon = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    sello = hashlib.sha256(canon.encode()).hexdigest()
    blob = cifrar(canon.encode())
    clave = f"backups/{usuario.id}/{sello[:16]}.json"
    modo = "s3"
    if _s3_listo():
        import boto3

        boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        ).put_object(Bucket=_bucket(), Key=clave, Body=blob.encode(), ContentType="application/json")
    else:
        modo = "hibrido"
        await guardar_habito({"usuario_id": str(usuario.id), "evento": "backup_hibrido", "sha256": sello, "clave": clave, "cifrado": blob})
    return {"modo": modo, "sha256": sello, "clave": clave, "cifrado": "AES-256-GCM", "snapshot": snapshot}
