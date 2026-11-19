"""Documentos KYC: S3 si hay credenciales, carpeta local si no."""

from pathlib import Path
from uuid import uuid4

from app.core.config import settings

LOCAL_ROOT = Path("data/kyc")


def _s3_configurado() -> bool:
    return bool(
        settings.aws_s3_kyc_bucket
        and settings.aws_access_key_id
        and settings.aws_secret_access_key
    )


def guardar_documento_kyc(*, usuario_id: str, filename: str, content: bytes, content_type: str) -> dict[str, str]:
    seguro = Path(filename).name or "documento"
    clave = f"kyc/{usuario_id}/{uuid4().hex}-{seguro}"
    if _s3_configurado():
        import boto3

        client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        client.put_object(
            Bucket=settings.aws_s3_kyc_bucket,
            Key=clave,
            Body=content,
            ContentType=content_type or "application/octet-stream",
        )
        return {
            "modo": "s3",
            "bucket": settings.aws_s3_kyc_bucket,
            "clave": clave,
        }

    destino = LOCAL_ROOT / usuario_id / Path(clave).name
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(content)
    return {"modo": "local", "clave": str(destino)}
