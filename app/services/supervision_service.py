"""Vínculo parental Senior → Junior y desvinculación con confirmación."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Cuenta, TipoCuenta
from app.models.supervision import EstadoSupervision, SupervisionCuenta
from app.models.user import Usuario
from app.schemas.supervision import SupervisionCreateRequest, SupervisionJuniorItem, SupervisionPublic
from app.services.exceptions import (
    AccountNotFound,
    ForbiddenAction,
    SupervisionConflict,
    SupervisionNotFound,
    UnlinkNotConfirmed,
    UserAccountMissing,
)


async def _cuenta_de_usuario(db: AsyncSession, usuario: Usuario) -> Cuenta:
    cuenta = await db.scalar(select(Cuenta).where(Cuenta.usuario_id == usuario.id))
    if cuenta is None:
        raise UserAccountMissing("El usuario no tiene cuenta transaccional")
    return cuenta


async def vincular(
    db: AsyncSession,
    senior: Usuario,
    payload: SupervisionCreateRequest,
) -> SupervisionPublic:
    if senior.rol != "SENIOR":
        raise ForbiddenAction("Solo un perfil Senior puede vincular cuentas")

    cuenta_senior = await _cuenta_de_usuario(db, senior)
    if cuenta_senior.tipo != TipoCuenta.SENIOR.value:
        raise ForbiddenAction("La cuenta del acudiente no es Senior")

    cuenta_junior = await db.scalar(select(Cuenta).where(Cuenta.id == payload.cuenta_junior_id))
    if cuenta_junior is None:
        raise AccountNotFound("Cuenta junior no encontrada")
    if cuenta_junior.tipo != TipoCuenta.JUNIOR.value:
        raise ForbiddenAction("El destino debe ser una cuenta Junior")
    if cuenta_junior.id == cuenta_senior.id:
        raise ForbiddenAction("No se puede vincular una cuenta consigo misma")

    activa_otro = await db.scalar(
        select(SupervisionCuenta).where(
            SupervisionCuenta.cuenta_junior_id == cuenta_junior.id,
            SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
            SupervisionCuenta.cuenta_senior_id != cuenta_senior.id,
        )
    )
    if activa_otro is not None:
        raise SupervisionConflict("La cuenta Junior ya tiene un acudiente activo")

    existente = await db.scalar(
        select(SupervisionCuenta).where(
            SupervisionCuenta.cuenta_senior_id == cuenta_senior.id,
            SupervisionCuenta.cuenta_junior_id == cuenta_junior.id,
        )
    )
    if existente is not None:
        if existente.estado == EstadoSupervision.ACTIVA.value:
            raise SupervisionConflict("El vínculo parental ya está activo")
        existente.estado = EstadoSupervision.ACTIVA.value
        existente.presupuesto_periodico = payload.presupuesto_periodico
        existente.periodicidad = payload.periodicidad
        existente.alerta_desvinculo = False
        existente.confirmado_desvinculo_en = None
        await db.commit()
        await db.refresh(existente)
        return SupervisionPublic.model_validate(existente)

    vinculo = SupervisionCuenta(
        cuenta_senior_id=cuenta_senior.id,
        cuenta_junior_id=cuenta_junior.id,
        presupuesto_periodico=payload.presupuesto_periodico,
        periodicidad=payload.periodicidad,
        estado=EstadoSupervision.ACTIVA.value,
    )
    db.add(vinculo)
    await db.commit()
    await db.refresh(vinculo)
    return SupervisionPublic.model_validate(vinculo)


async def listar_juniors(db: AsyncSession, senior: Usuario) -> list[SupervisionJuniorItem]:
    cuenta_senior = await _cuenta_de_usuario(db, senior)
    result = await db.execute(
        select(SupervisionCuenta)
        .options(selectinload(SupervisionCuenta.cuenta_junior).selectinload(Cuenta.usuario))
        .where(
            SupervisionCuenta.cuenta_senior_id == cuenta_senior.id,
            SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
        )
    )
    items: list[SupervisionJuniorItem] = []
    for vinculo in result.scalars().all():
        junior_cta = vinculo.cuenta_junior
        junior_user = junior_cta.usuario
        items.append(
            SupervisionJuniorItem(
                supervision_id=vinculo.id,
                cuenta_junior_id=junior_cta.id,
                email=junior_user.email,
                nombres=junior_user.nombres,
                apellidos=junior_user.apellidos,
                saldo=junior_cta.saldo,
                moneda=junior_cta.moneda,
                presupuesto_periodico=vinculo.presupuesto_periodico,
                periodicidad=vinculo.periodicidad,
                estado=vinculo.estado,
                limite_gasto_diario=junior_cta.limite_gasto_diario,
                limite_gasto_semanal=junior_cta.limite_gasto_semanal,
                limite_gasto_mensual=junior_cta.limite_gasto_mensual,
                tarjeta_bloqueada=junior_cta.tarjeta_bloqueada,
            )
        )
    return items


async def desvincular(
    db: AsyncSession,
    senior: Usuario,
    supervision_id: UUID,
    *,
    confirmacion: bool,
) -> SupervisionPublic:
    if not confirmacion:
        raise UnlinkNotConfirmed(
            "Debes confirmar la desvinculación (confirmacion=true). "
            "El menor dejará de estar bajo tu supervisión."
        )

    cuenta_senior = await _cuenta_de_usuario(db, senior)
    vinculo = await db.scalar(
        select(SupervisionCuenta).where(SupervisionCuenta.id == supervision_id)
    )
    if vinculo is None:
        raise SupervisionNotFound("Vínculo de supervisión no encontrado")
    if vinculo.cuenta_senior_id != cuenta_senior.id:
        raise ForbiddenAction("No puedes desvincular un vínculo de otro acudiente")
    if vinculo.estado == EstadoSupervision.DESVINCULADA.value:
        raise SupervisionConflict("El vínculo ya está desvinculado")

    vinculo.estado = EstadoSupervision.DESVINCULADA.value
    vinculo.alerta_desvinculo = True
    vinculo.confirmado_desvinculo_en = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(vinculo)
    return SupervisionPublic.model_validate(vinculo)


async def exigir_supervision_activa(
    db: AsyncSession,
    cuenta_senior_id: UUID,
    cuenta_junior_id: UUID,
) -> SupervisionCuenta:
    vinculo = await db.scalar(
        select(SupervisionCuenta).where(
            SupervisionCuenta.cuenta_senior_id == cuenta_senior_id,
            SupervisionCuenta.cuenta_junior_id == cuenta_junior_id,
            SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
        )
    )
    if vinculo is None:
        raise SupervisionNotFound("No hay supervisión activa entre estas cuentas")
    return vinculo
