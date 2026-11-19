"""Vinculación familiar con consentimiento. No hay vínculo hasta que el Junior acepta."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.account import Cuenta, CuentaJunior, TipoCuenta
from app.models.invitation import EstadoInvitacion, FamilyInvitation
from app.models.supervision import EstadoSupervision, PeriodicidadPresupuesto, SupervisionCuenta
from app.models.transaction import TipoTransaccion, Transaccion
from app.models.user import RolUsuario, Usuario
from app.schemas.supervision import (
    ActivityItem,
    CardStatusResponse,
    CreateJuniorRequest,
    InvitationPublic,
    InviteRequest,
)
from app.services.account_service import get_cuenta_usuario
from app.services.exceptions import (
    AccountNotFound,
    EmailAlreadyRegistered,
    FamilyTaken,
    ForbiddenAction,
    InsufficientFunds,
    InvitationNotFound,
    SeniorNotLinkable,
    SupervisionNotFound,
    UserAccountMissing,
)
from app.services.ledger_service import transferir

MSG_SENIOR = "Esta cuenta pertenece a un Senior independiente y no puede ser vinculada como dependiente"
MSG_NUCLEO = "Esta cuenta ya pertenece a otro núcleo familiar"
MSG_NO_EXISTE = "No existe una cuenta con ese correo. Usa create-junior para crearla."


async def _usuario_por_email(db: AsyncSession, email: str) -> Usuario | None:
    return await db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))


async def _supervision_activa(db: AsyncSession, cuenta_junior_id: UUID) -> SupervisionCuenta | None:
    return await db.scalar(
        select(SupervisionCuenta).where(
            SupervisionCuenta.cuenta_junior_id == cuenta_junior_id,
            SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
        )
    )


def _publica(invitation: FamilyInvitation, senior: Usuario, junior: Usuario | None = None) -> InvitationPublic:
    return InvitationPublic(
        id=invitation.id,
        senior_id=invitation.senior_id,
        junior_id=invitation.junior_id,
        senior_nombre=f"{senior.nombres} {senior.apellidos}".strip(),
        junior_nombre=f"{junior.nombres} {junior.apellidos}".strip() if junior else "",
        junior_email=junior.email if junior else "",
        initial_budget=invitation.initial_budget,
        daily_limit=invitation.daily_limit,
        weekly_limit=invitation.weekly_limit,
        monthly_limit=invitation.monthly_limit,
        estado=invitation.estado,
    )


async def invitar(db: AsyncSession, senior: Usuario, payload: InviteRequest) -> InvitationPublic:
    junior = await _usuario_por_email(db, payload.email)
    if junior is None:
        raise AccountNotFound(MSG_NO_EXISTE)
    if junior.rol == RolUsuario.SENIOR.value:
        raise SeniorNotLinkable(MSG_SENIOR)
    if junior.rol != RolUsuario.JUNIOR.value:
        raise SeniorNotLinkable(MSG_SENIOR)

    cuenta_junior = await db.scalar(select(Cuenta).where(Cuenta.usuario_id == junior.id))
    if cuenta_junior is None:
        raise UserAccountMissing("El Junior no tiene cuenta transaccional")
    activa = await _supervision_activa(db, cuenta_junior.id)
    if activa is not None:
        raise FamilyTaken(MSG_NUCLEO)

    pendiente = await db.scalar(
        select(FamilyInvitation).where(
            FamilyInvitation.senior_id == senior.id,
            FamilyInvitation.junior_id == junior.id,
            FamilyInvitation.estado == EstadoInvitacion.PENDING.value,
        )
    )
    if pendiente is None:
        pendiente = FamilyInvitation(
            senior_id=senior.id,
            junior_id=junior.id,
            initial_budget=payload.initial_budget,
            daily_limit=payload.daily_limit,
            weekly_limit=payload.weekly_limit,
            monthly_limit=payload.monthly_limit,
            estado=EstadoInvitacion.PENDING.value,
        )
        db.add(pendiente)
    else:
        pendiente.initial_budget = payload.initial_budget
        pendiente.daily_limit = payload.daily_limit
        pendiente.weekly_limit = payload.weekly_limit
        pendiente.monthly_limit = payload.monthly_limit
    await db.commit()
    await db.refresh(pendiente)
    return _publica(pendiente, senior, junior)


async def crear_junior(db: AsyncSession, senior: Usuario, payload: CreateJuniorRequest) -> InvitationPublic:
    existente = await _usuario_por_email(db, payload.email)
    if existente is not None:
        if existente.rol == RolUsuario.SENIOR.value:
            raise SeniorNotLinkable(MSG_SENIOR)
        raise EmailAlreadyRegistered("Ese correo ya existe. Envíale una invitación.")

    junior = Usuario(
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
        nombres=payload.nombres.strip(),
        apellidos=payload.apellidos.strip(),
        rol=RolUsuario.JUNIOR.value,
        moneda_preferida=senior.moneda_preferida,
    )
    db.add(junior)
    await db.flush()
    cuenta_senior = await get_cuenta_usuario(db, senior)
    cuenta_junior = CuentaJunior(
        usuario_id=junior.id,
        tipo=TipoCuenta.JUNIOR.value,
        moneda=cuenta_senior.moneda,
        limite_gasto_diario=payload.daily_limit,
        limite_gasto_semanal=payload.weekly_limit,
        limite_gasto_mensual=payload.monthly_limit,
    )
    db.add(cuenta_junior)
    await db.flush()
    vinculo = SupervisionCuenta(
        cuenta_senior_id=cuenta_senior.id,
        cuenta_junior_id=cuenta_junior.id,
        presupuesto_periodico=payload.monthly_limit,
        periodicidad=PeriodicidadPresupuesto.MENSUAL.value,
        estado=EstadoSupervision.ACTIVA.value,
    )
    db.add(vinculo)
    invitacion = FamilyInvitation(
        senior_id=senior.id,
        junior_id=junior.id,
        initial_budget=payload.initial_budget,
        daily_limit=payload.daily_limit,
        weekly_limit=payload.weekly_limit,
        monthly_limit=payload.monthly_limit,
        estado=EstadoInvitacion.ACCEPTED.value,
    )
    db.add(invitacion)
    await db.flush()
    if payload.initial_budget > 0:
        if Decimal(cuenta_senior.saldo) < payload.initial_budget:
            raise InsufficientFunds("Fondos insuficientes para la mesada inicial")
        await transferir(
            db,
            origen_id=cuenta_senior.id,
            destino_id=cuenta_junior.id,
            monto=payload.initial_budget,
            iniciada_por_usuario_id=senior.id,
            tipo=TipoTransaccion.ASIGNACION_PRESUPUESTO.value,
            descripcion="Mesada inicial al crear la cuenta Junior",
        )
    else:
        await db.commit()
    await db.refresh(invitacion)
    return _publica(invitacion, senior)


async def listar_pendientes(db: AsyncSession, junior: Usuario) -> list[InvitationPublic]:
    rows = (
        await db.scalars(
            select(FamilyInvitation).where(
                FamilyInvitation.junior_id == junior.id,
                FamilyInvitation.estado == EstadoInvitacion.PENDING.value,
            )
        )
    ).all()
    salida: list[InvitationPublic] = []
    for row in rows:
        senior = await db.get(Usuario, row.senior_id)
        if senior is not None:
            salida.append(_publica(row, senior, junior))
    return salida


async def listar_enviadas(db: AsyncSession, senior: Usuario) -> list[InvitationPublic]:
    rows = (
        await db.scalars(
            select(FamilyInvitation).where(
                FamilyInvitation.senior_id == senior.id,
                FamilyInvitation.estado == EstadoInvitacion.PENDING.value,
            )
        )
    ).all()
    salida: list[InvitationPublic] = []
    for row in rows:
        junior = await db.get(Usuario, row.junior_id)
        if junior is not None:
            salida.append(_publica(row, senior, junior))
    return salida


async def responder(
    db: AsyncSession,
    junior: Usuario,
    invitation_id: UUID,
    accept: bool,
) -> InvitationPublic:
    invitation = await db.get(FamilyInvitation, invitation_id)
    if invitation is None or invitation.junior_id != junior.id:
        raise InvitationNotFound("Invitación no encontrada")
    if invitation.estado != EstadoInvitacion.PENDING.value:
        raise FamilyTaken("Esta invitación ya fue respondida")
    senior = await db.get(Usuario, invitation.senior_id)
    if senior is None:
        raise InvitationNotFound("El Senior de la invitación ya no existe")

    if not accept:
        invitation.estado = EstadoInvitacion.REJECTED.value
        await db.commit()
        await db.refresh(invitation)
        return _publica(invitation, senior)

    cuenta_junior = await db.scalar(select(Cuenta).where(Cuenta.usuario_id == junior.id))
    cuenta_senior = await db.scalar(select(Cuenta).where(Cuenta.usuario_id == senior.id))
    if cuenta_junior is None or cuenta_senior is None:
        raise UserAccountMissing("Falta la cuenta de uno de los dos perfiles")
    if await _supervision_activa(db, cuenta_junior.id):
        raise FamilyTaken(MSG_NUCLEO)

    cuenta_junior.limite_gasto_diario = invitation.daily_limit
    cuenta_junior.limite_gasto_semanal = invitation.weekly_limit
    cuenta_junior.limite_gasto_mensual = invitation.monthly_limit
    db.add(
        SupervisionCuenta(
            cuenta_senior_id=cuenta_senior.id,
            cuenta_junior_id=cuenta_junior.id,
            presupuesto_periodico=invitation.monthly_limit,
            periodicidad=PeriodicidadPresupuesto.MENSUAL.value,
            estado=EstadoSupervision.ACTIVA.value,
        )
    )
    invitation.estado = EstadoInvitacion.ACCEPTED.value
    otras = (
        await db.scalars(
            select(FamilyInvitation).where(
                FamilyInvitation.junior_id == junior.id,
                FamilyInvitation.estado == EstadoInvitacion.PENDING.value,
                FamilyInvitation.id != invitation.id,
            )
        )
    ).all()
    for otra in otras:
        otra.estado = EstadoInvitacion.REJECTED.value
    if invitation.initial_budget > 0:
        if Decimal(cuenta_senior.saldo) < invitation.initial_budget:
            raise InsufficientFunds("El Senior no tiene saldo para la mesada inicial")
        await transferir(
            db,
            origen_id=cuenta_senior.id,
            destino_id=cuenta_junior.id,
            monto=invitation.initial_budget,
            iniciada_por_usuario_id=senior.id,
            tipo=TipoTransaccion.ASIGNACION_PRESUPUESTO.value,
            descripcion="Mesada inicial aceptada por el Junior",
        )
    else:
        await db.commit()
    await db.refresh(invitation)
    return _publica(invitation, senior)


def _es_hormiga(tx: Transaccion, grupo: set[UUID]) -> bool:
    return tx.id in grupo


async def actividad(db: AsyncSession, senior: Usuario, cuenta_junior_id: UUID) -> list[ActivityItem]:
    from app.services.neobank_service import ids_hormiga

    cuenta_senior = await get_cuenta_usuario(db, senior)
    vinculo = await db.scalar(
        select(SupervisionCuenta).where(
            SupervisionCuenta.cuenta_senior_id == cuenta_senior.id,
            SupervisionCuenta.cuenta_junior_id == cuenta_junior_id,
            SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
        )
    )
    if vinculo is None:
        raise SupervisionNotFound("Ese Junior no está en tu núcleo familiar")
    cuenta_junior = await db.get(Cuenta, cuenta_junior_id)
    if cuenta_junior is None:
        raise AccountNotFound("Cuenta junior no encontrada")
    movimientos = (
        await db.scalars(
            select(Transaccion)
            .where(
                Transaccion.iniciada_por_usuario_id == cuenta_junior.usuario_id,
                Transaccion.tipo == TipoTransaccion.COMPRA.value,
            )
            .order_by(Transaccion.created_at.desc())
            .limit(30)
        )
    ).all()
    hormiga = ids_hormiga(list(movimientos))
    return [
        ActivityItem(
            id=tx.id,
            categoria=tx.categoria,
            metodo_pago=tx.metodo_pago,
            fecha=tx.created_at,
            monto=tx.monto,
            descripcion=tx.descripcion,
            is_impulsive=bool(tx.is_impulsive or tx.forzada),
            es_hormiga=_es_hormiga(tx, hormiga),
        )
        for tx in movimientos
    ]


async def cambiar_tarjeta(
    db: AsyncSession,
    senior: Usuario,
    cuenta_junior_id: UUID,
    bloqueada: bool,
) -> CardStatusResponse:
    cuenta_senior = await get_cuenta_usuario(db, senior)
    vinculo = await db.scalar(
        select(SupervisionCuenta).where(
            SupervisionCuenta.cuenta_senior_id == cuenta_senior.id,
            SupervisionCuenta.cuenta_junior_id == cuenta_junior_id,
            SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
        )
    )
    if vinculo is None:
        raise ForbiddenAction("Solo puedes bloquear la tarjeta de un Junior de tu núcleo")
    cuenta = await db.get(Cuenta, cuenta_junior_id)
    if cuenta is None or cuenta.tipo != TipoCuenta.JUNIOR.value:
        raise AccountNotFound("Cuenta junior no encontrada")
    cuenta.tarjeta_bloqueada = bloqueada
    await db.commit()
    return CardStatusResponse(cuenta_junior_id=cuenta.id, tarjeta_bloqueada=cuenta.tarjeta_bloqueada)


async def actualizar_limites(
    db: AsyncSession,
    senior: Usuario,
    cuenta_junior_id: UUID,
    daily_limit: Decimal,
    weekly_limit: Decimal,
    monthly_limit: Decimal,
):
    from app.schemas.supervision import LimitsResponse

    cuenta_senior = await get_cuenta_usuario(db, senior)
    vinculo = await db.scalar(
        select(SupervisionCuenta).where(
            SupervisionCuenta.cuenta_senior_id == cuenta_senior.id,
            SupervisionCuenta.cuenta_junior_id == cuenta_junior_id,
            SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
        )
    )
    if vinculo is None:
        raise ForbiddenAction("Solo puedes editar límites de un Junior de tu núcleo")
    cuenta = await db.get(Cuenta, cuenta_junior_id)
    if cuenta is None:
        raise AccountNotFound("Cuenta junior no encontrada")
    cuenta.limite_gasto_diario = daily_limit
    cuenta.limite_gasto_semanal = weekly_limit
    cuenta.limite_gasto_mensual = monthly_limit
    vinculo.presupuesto_periodico = monthly_limit
    await db.commit()
    return LimitsResponse(
        cuenta_junior_id=cuenta.id,
        daily_limit=daily_limit,
        weekly_limit=weekly_limit,
        monthly_limit=monthly_limit,
    )
