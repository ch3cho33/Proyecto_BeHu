"""Carga simulada de documento KYC (local o S3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.storage import guardar_documento_kyc
from app.models.user import KycStatus, Usuario

router = APIRouter(prefix="/kyc", tags=["kyc"])


@router.post("/document")
async def upload_kyc(
    user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    archivo: UploadFile = File(...),
) -> dict[str, str]:
    contenido = await archivo.read()
    if not contenido:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="El archivo está vacío")
    guardado = guardar_documento_kyc(
        usuario_id=str(user.id),
        filename=archivo.filename or "documento",
        content=contenido,
        content_type=archivo.content_type or "application/octet-stream",
    )
    user.kyc_status = KycStatus.IN_REVIEW.value
    await db.commit()
    guardado["kyc_status"] = user.kyc_status
    return guardado
