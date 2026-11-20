"""Consolida alertas de gasto, límites e invitaciones en la campana."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Cuenta
from app.models.invitation import FamilyInvitation
from app.models.notification import Notificacion
from app.models.supervision import EstadoSupervision, SupervisionCuenta
from app.models.transaction import EstadoTransaccion, TipoTransaccion, Transaccion
from app.models.user import Usuario
from app.schemas.catalog import NotificationPublic
from app.services.account_service import get_cuenta_usuario
from app.services.behu_mini_ai import termino_no_pertinente
from app.services.exceptions import DomainError
from app.services.neobank_service import ids_hormiga


class NotificacionNoEncontrada(DomainError):
    status_code = 404


def _item(clave: str, tipo: str, severity: str, titulo: str, detalle: str, sugerencia: str) -> dict:
    return {
        "clave": clave,
        "tipo": tipo,
        "severity": severity,
        "titulo": titulo,
        "detalle": detalle,
        "sugerencia": sugerencia,
    }


async def _gastado(db: AsyncSession, usuario_id, desde: datetime) -> Decimal:
    total = await db.scalar(
        select(func.coalesce(func.sum(Transaccion.monto), 0)).where(
            Transaccion.iniciada_por_usuario_id == usuario_id,
            Transaccion.tipo == TipoTransaccion.COMPRA.value,
            Transaccion.estado == EstadoTransaccion.COMPLETADA.value,
            Transaccion.created_at >= desde,
        )
    )
    return Decimal(total or 0)


async def _compras(db: AsyncSession, usuario_id) -> list[Transaccion]:
    return list(
        (
            await db.scalars(
                select(Transaccion)
                .where(
                    Transaccion.iniciada_por_usuario_id == usuario_id,
                    Transaccion.tipo == TipoTransaccion.COMPRA.value,
                    Transaccion.estado == EstadoTransaccion.COMPLETADA.value,
                )
                .order_by(Transaccion.created_at.desc())
                .limit(40)
            )
        ).all()
    )


def _avisos_de_compras(compras: list[Transaccion], prefijo: str) -> list[dict]:
    avisos: list[dict] = []
    for tx in compras:
        termino = termino_no_pertinente(tx.notas, tx.comercio, tx.descripcion, tx.categoria)
        if termino:
            avisos.append(
                _item(
                    f"vicio:{tx.id}",
                    "GASTO_NO_PERTINENTE",
                    "high",
                    "Gasto no pertinente",
                    f"{prefijo}{termino} por {Decimal(tx.monto):.0f}.",
                    "Redirige ese monto a una meta activa o activa el redondeo automático.",
                )
            )
        if tx.is_impulsive or tx.forzada:
            avisos.append(
                _item(
                    f"impulso:{tx.id}",
                    "GASTO_IMPULSIVO",
                    "medium",
                    "Gasto impulsivo",
                    f"{prefijo}compra confirmada por {Decimal(tx.monto):.0f} después del freno de BeHu Mini.",
                    "Revisa el movimiento y baja el límite si se repite.",
                )
            )
    if ids_hormiga(compras):
        avisos.append(
            _item(
                f"hormiga:{compras[0].iniciada_por_usuario_id}",
                "GASTO_HORMIGA",
                "medium",
                "Gastos hormiga",
                f"{prefijo}tres o más compras pequeñas de comida u ocio en 48 horas.",
                "Aparta ese monto en una meta antes de la siguiente compra.",
            )
        )
    return avisos


async def _avisos_limite(db: AsyncSession, cuenta: Cuenta, prefijo: str) -> list[dict]:
    ahora = datetime.now(timezone.utc)
    avisos: list[dict] = []
    pares = (
        ("diario", cuenta.limite_gasto_diario, ahora - timedelta(days=1)),
        ("semanal", cuenta.limite_gasto_semanal, ahora - timedelta(days=7)),
    )
    for nombre, tope, desde in pares:
        if not tope or Decimal(tope) <= 0:
            continue
        gastado = await _gastado(db, cuenta.usuario_id, desde)
        if gastado >= Decimal(tope) * Decimal("0.8"):
            avisos.append(
                _item(
                    f"limite:{nombre}:{cuenta.id}:{ahora.date().isoformat()}",
                    "LIMITE",
                    "high",
                    "Límite de gasto",
                    f"{prefijo}llevas {gastado:.0f} de un tope {nombre} de {Decimal(tope):.0f}.",
                    "Pausa las compras discrecionales o pide un ajuste de límite.",
                )
            )
    return avisos


async def _construir(db: AsyncSession, usuario: Usuario) -> list[dict]:
    cuenta = await get_cuenta_usuario(db, usuario)
    avisos: list[dict] = []
    if usuario.rol == "JUNIOR":
        avisos.extend(_avisos_de_compras(await _compras(db, usuario.id), "Registraste "))
        avisos.extend(await _avisos_limite(db, cuenta, "Tu cuenta "))
        pendientes = (
            await db.scalars(
                select(FamilyInvitation).where(
                    FamilyInvitation.junior_id == usuario.id,
                    FamilyInvitation.estado == "PENDING",
                )
            )
        ).all()
        for invite in pendientes:
            avisos.append(
                _item(
                    f"invite:{invite.id}",
                    "INVITACION",
                    "info",
                    "Invitación familiar",
                    "Tienes una invitación pendiente de un Senior.",
                    "Acéptala o recházala desde Inicio.",
                )
            )
        return avisos

    vinculos = (
        await db.scalars(
            select(SupervisionCuenta).where(
                SupervisionCuenta.cuenta_senior_id == cuenta.id,
                SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
            )
        )
    ).all()
    for vinculo in vinculos:
        junior_cuenta = await db.get(Cuenta, vinculo.cuenta_junior_id)
        if junior_cuenta is None:
            continue
        junior = await db.get(Usuario, junior_cuenta.usuario_id)
        nombre = f"{junior.nombres} " if junior else "Tu Junior "
        avisos.extend(_avisos_de_compras(await _compras(db, junior_cuenta.usuario_id), f"{nombre}registró "))
        avisos.extend(await _avisos_limite(db, junior_cuenta, f"{nombre}"))
    enviadas = (
        await db.scalars(
            select(FamilyInvitation).where(
                FamilyInvitation.senior_id == usuario.id,
                FamilyInvitation.estado == "PENDING",
            )
        )
    ).all()
    for invite in enviadas:
        invitado = await db.get(Usuario, invite.junior_id)
        correo = invitado.email if invitado else "un Junior"
        avisos.append(
            _item(
                f"invite-sent:{invite.id}",
                "INVITACION",
                "info",
                "Invitación enviada",
                f"La invitación a {correo} sigue pendiente.",
                "Espera la respuesta del Junior antes de transferir otra mesada.",
            )
        )
    return avisos


async def listar(db: AsyncSession, usuario: Usuario) -> list[NotificationPublic]:
    deseadas = await _construir(db, usuario)
    existentes = (
        await db.scalars(select(Notificacion).where(Notificacion.usuario_id == usuario.id))
    ).all()
    claves = {item.clave for item in existentes}
    for aviso in deseadas:
        if aviso["clave"] in claves:
            continue
        db.add(Notificacion(usuario_id=usuario.id, **aviso))
    if deseadas:
        await db.commit()
    filas = (
        await db.scalars(
            select(Notificacion).where(Notificacion.usuario_id == usuario.id).order_by(Notificacion.created_at.desc())
        )
    ).all()
    return [NotificationPublic.model_validate(fila, from_attributes=True) for fila in filas]


async def marcar_leida(db: AsyncSession, usuario: Usuario, notificacion_id) -> NotificationPublic:
    fila = await db.get(Notificacion, notificacion_id)
    if fila is None or fila.usuario_id != usuario.id:
        raise NotificacionNoEncontrada("Notificación no encontrada")
    fila.leida = True
    await db.commit()
    await db.refresh(fila)
    return NotificationPublic.model_validate(fila, from_attributes=True)
