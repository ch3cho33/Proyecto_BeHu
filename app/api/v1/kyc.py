"""Carga simulada de documento KYC (local o S3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.dependencies import get_current_user
from app.core.storage import guardar_documento_kyc
from app.models.user import Usuario

router = APIRouter(prefix="/kyc", tags=["kyc"])


@router.post("/document")
async def upload_kyc(
    user: Annotated[Usuario, Depends(get_current_user)],
    archivo: UploadFile = File(...),
) -> dict[str, str]:
    contenido = await archivo.read()
    if not contenido:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="El archivo está vacío")
    return guardar_documento_kyc(
        usuario_id=str(user.id),
        filename=archivo.filename or "documento",
        content=contenido,
        content_type=archivo.content_type or "application/octet-stream",
    )
