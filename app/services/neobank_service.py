"""Ingresos, gastos con bucket 50/30/20 y detección de gastos hormiga."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Cuenta, TipoCuenta
from app.models.goal import EstadoMeta, MetaAhorro
from app.models.ledger import LedgerContable, NaturalezaAsiento
from app.models.transaction import EstadoTransaccion, TipoTransaccion, Transaccion
from app.models.user import Usuario
from app.schemas.transaction import IncomeRequest, MovementRequest
from app.services.account_service import get_cuenta_usuario
from app.services.exceptions import AccountNotFound, CardBlocked
from app.services.ledger_service import transferir, vuelto_redondeo
from app.schemas.transaction import SpendRequest
from app.services.spend_service import simular_compra

HORMIGA_CATEGORIAS = frozenset({"COMIDA", "ENTRETENIMIENTO", "OCIO"})
HORMIGA_TOPE = Decimal("80000.00")
VENTANA_HORMIGA = timedelta(hours=48)


def _categoria(codigo: str) -> str:
    if codigo == "OCIO":
        return "ENTRETENIMIENTO"
    return codigo


def ids_hormiga(movimientos: list[Transaccion]) -> set[UUID]:
    """Tres o más compras pequeñas de comida u ocio dentro de 48 horas."""
    candidatas = [
        tx
        for tx in movimientos
        if tx.tipo == TipoTransaccion.COMPRA.value
        and tx.estado == EstadoTransaccion.COMPLETADA.value
        and (tx.categoria or "") in HORMIGA_CATEGORIAS
        and Decimal(tx.monto) <= HORMIGA_TOPE
        and tx.created_at is not None
    ]
    marcadas: set[UUID] = set()
    ordenadas = sorted(candidatas, key=lambda tx: tx.created_at)
    for indice, actual in enumerate(ordenadas):
        grupo = [actual]
        for vecina in ordenadas[indice + 1 :]:
            if vecina.created_at - actual.created_at <= VENTANA_HORMIGA:
                grupo.append(vecina)
            else:
                break
        if len(grupo) >= 3:
            marcadas.update(tx.id for tx in grupo)
    return marcadas


async def registrar(db: AsyncSession, usuario: Usuario, payload: MovementRequest) -> tuple[Transaccion, Decimal, str | None]:
    if payload.tipo == "INGRESO":
        ingreso = await registrar_ingreso(
            db,
            usuario,
            IncomeRequest(monto=payload.monto, descripcion=payload.notas, bucket=payload.bucket),
        )
        return ingreso, Decimal("0.00"), None
    compra = SpendRequest(
        monto=payload.monto,
        categoria=_categoria(payload.categoria),
        comercio=payload.notas or payload.categoria,
        descripcion=payload.notas,
        forzar_confirmacion=payload.forzar_confirmacion,
    )
    transaccion = await simular_compra(db, usuario, compra, commit=False)
    transaccion.metodo_pago = payload.metodo_pago
    transaccion.notas = payload.notas
    transaccion.recurrencia = payload.recurrencia
    transaccion.bucket = payload.bucket
    transaccion.is_impulsive = bool(payload.forzar_confirmacion)
    redondeo = Decimal("0.00")
    meta_nombre: str | None = None
    if payload.redondear_ahorro:
        redondeo, meta_nombre = await _aplicar_redondeo(db, usuario, Decimal(payload.monto))
    await db.commit()
    await db.refresh(transaccion)
    return transaccion, redondeo, meta_nombre


async def _aplicar_redondeo(db: AsyncSession, usuario: Usuario, monto: Decimal) -> tuple[Decimal, str | None]:
    from app.models.goal import EstadoMeta, MetaAhorro
    from app.services.sandbox_accounts import META_EMAIL, obtener_cuenta_sistema

    vuelto = vuelto_redondeo(monto)
    if vuelto <= 0:
        return Decimal("0.00"), None
    cuenta = await get_cuenta_usuario(db, usuario)
    meta = await db.scalar(
        select(MetaAhorro)
        .where(MetaAhorro.cuenta_id == cuenta.id, MetaAhorro.estado == EstadoMeta.ACTIVA.value)
        .order_by(MetaAhorro.created_at.asc())
    )
    if meta is None:
        return Decimal("0.00"), None
    restante = Decimal(meta.monto_objetivo) - Decimal(meta.monto_actual)
    if Decimal(cuenta.saldo) < vuelto or vuelto > restante:
        return Decimal("0.00"), None
    boveda = await obtener_cuenta_sistema(db, META_EMAIL)
    await transferir(
        db,
        origen_id=cuenta.id,
        destino_id=boveda.id,
        monto=vuelto,
        iniciada_por_usuario_id=usuario.id,
        tipo=TipoTransaccion.ABONO_META.value,
        descripcion=f"Redondeo automático a {meta.nombre}",
        commit=False,
    )
    meta.monto_actual = Decimal(meta.monto_actual) + vuelto
    if meta.monto_actual >= Decimal(meta.monto_objetivo):
        meta.estado = EstadoMeta.COMPLETADA.value
    return vuelto, meta.nombre


async def registrar_ingreso(db: AsyncSession, usuario: Usuario, payload: IncomeRequest) -> Transaccion:
    cuenta = await get_cuenta_usuario(db, usuario)
    if cuenta.tarjeta_bloqueada and cuenta.tipo == TipoCuenta.JUNIOR.value:
        raise CardBlocked("La tarjeta de este Junior está bloqueada por el acudiente")
    equity = await db.scalar(select(Cuenta).where(Cuenta.tipo == TipoCuenta.SANDBOX_EQUITY.value))
    if equity is None:
        raise AccountNotFound("El sandbox no tiene cuenta de capital para simular el ingreso")
    return await transferir(
        db,
        origen_id=equity.id,
        destino_id=cuenta.id,
        monto=payload.monto,
        iniciada_por_usuario_id=usuario.id,
        tipo=TipoTransaccion.INGRESO.value,
        descripcion=payload.descripcion or "Ingreso simulado",
        es_transferencia_global=False,
        bucket=payload.bucket,
        notas=payload.descripcion,
        metodo_pago="TRANSFERENCIA",
    )


async def resumen_503020(db: AsyncSession, usuario: Usuario) -> dict:
    cuenta = await get_cuenta_usuario(db, usuario)
    ahora = datetime.now(timezone.utc)
    inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ingresos = await db.scalar(
        select(func.coalesce(func.sum(Transaccion.monto), 0)).where(
            Transaccion.iniciada_por_usuario_id == usuario.id,
            Transaccion.tipo == TipoTransaccion.INGRESO.value,
            Transaccion.estado == EstadoTransaccion.COMPLETADA.value,
            Transaccion.created_at >= inicio,
        )
    )
    ingresos_mes = Decimal(str(ingresos or 0))
    if usuario.rol == "JUNIOR" and ingresos_mes == 0:
        asignado = await db.scalar(
            select(func.coalesce(func.sum(LedgerContable.monto), 0))
            .join(Transaccion, Transaccion.id == LedgerContable.transaccion_id)
            .where(
                LedgerContable.cuenta_id == cuenta.id,
                LedgerContable.naturaleza == NaturalezaAsiento.CREDITO.value,
                Transaccion.tipo == TipoTransaccion.ASIGNACION_PRESUPUESTO.value,
                Transaccion.created_at >= inicio,
            )
        )
        ingresos_mes = Decimal(str(asignado or 0))

    async def _bucket(nombre: str) -> Decimal:
        total = await db.scalar(
            select(func.coalesce(func.sum(Transaccion.monto), 0)).where(
                Transaccion.iniciada_por_usuario_id == usuario.id,
                Transaccion.tipo == TipoTransaccion.COMPRA.value,
                Transaccion.estado == EstadoTransaccion.COMPLETADA.value,
                Transaccion.bucket == nombre,
                Transaccion.created_at >= inicio,
            )
        )
        return Decimal(str(total or 0))

    ahorro_meta = await db.scalar(
        select(func.coalesce(func.sum(Transaccion.monto), 0)).where(
            Transaccion.iniciada_por_usuario_id == usuario.id,
            Transaccion.tipo == TipoTransaccion.ABONO_META.value,
            Transaccion.estado == EstadoTransaccion.COMPLETADA.value,
            Transaccion.created_at >= inicio,
        )
    )
    necesidades = await _bucket("NECESIDADES")
    deseos = await _bucket("DESEOS")
    ahorro = await _bucket("AHORRO") + Decimal(str(ahorro_meta or 0))
    metas = await db.scalar(
        select(func.coalesce(func.sum(MetaAhorro.monto_actual), 0)).where(
            MetaAhorro.cuenta_id == cuenta.id,
            MetaAhorro.estado != EstadoMeta.CANCELADA.value,
        )
    )

    def barra(real: Decimal, peso: Decimal) -> dict[str, str]:
        objetivo = (ingresos_mes * peso).quantize(Decimal("0.01"))
        return {"objetivo": f"{objetivo:.2f}", "real": f"{real:.2f}", "peso": f"{peso:.2f}"}

    return {
        "ingresos": f"{ingresos_mes:.2f}",
        "moneda": cuenta.moneda,
        "saldo_disponible": f"{Decimal(cuenta.saldo):.2f}",
        "saldo_congelado": f"{Decimal(str(metas or 0)):.2f}",
        "necesidades": barra(necesidades, Decimal("0.50")),
        "deseos": barra(deseos, Decimal("0.30")),
        "ahorro": barra(ahorro, Decimal("0.20")),
    }
