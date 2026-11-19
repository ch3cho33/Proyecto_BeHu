"""Índice de salud financiera Score BeHu (0-100)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.education import ProgresoEducativo
from app.models.goal import EstadoMeta, MetaAhorro
from app.models.ledger import LedgerContable, NaturalezaAsiento
from app.models.transaction import EstadoTransaccion, TipoTransaccion, Transaccion
from app.models.user import Usuario
from app.schemas.scoring import ScoreFactor, ScoreResponse
from app.services.account_service import get_cuenta_usuario

BASE = 50
MAX_METAS = 16
MAX_EDUCACION = 24
MAX_IMPULSO = 24


def _nivel(puntaje: int) -> tuple[str, str]:
    if puntaje >= 80:
        return "Excelente", "#1f7a4d"
    if puntaje >= 60:
        return "Saludable", "#3d9b68"
    if puntaje >= 40:
        return "En Construcción", "#c4922a"
    return "Crítico", "#b42318"


async def _gastado_desde(db: AsyncSession, cuenta_id, desde: datetime) -> Decimal:
    total = await db.scalar(
        select(func.coalesce(func.sum(LedgerContable.monto), 0))
        .join(Transaccion, Transaccion.id == LedgerContable.transaccion_id)
        .where(
            LedgerContable.cuenta_id == cuenta_id,
            LedgerContable.naturaleza == NaturalezaAsiento.DEBITO.value,
            Transaccion.tipo == TipoTransaccion.COMPRA.value,
            Transaccion.estado == EstadoTransaccion.COMPLETADA.value,
            Transaccion.created_at >= desde,
        )
    )
    return Decimal(str(total))


async def calcular_score(db: AsyncSession, usuario: Usuario) -> ScoreResponse:
    cuenta = await get_cuenta_usuario(db, usuario)
    ahora = datetime.now(timezone.utc)
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_semana = inicio_dia - timedelta(days=inicio_dia.weekday())
    hace_30 = ahora - timedelta(days=30)

    metas = (
        await db.scalars(select(MetaAhorro).where(MetaAhorro.cuenta_id == cuenta.id))
    ).all()
    metas_con_abono = [
        meta
        for meta in metas
        if meta.estado != EstadoMeta.CANCELADA.value and Decimal(meta.monto_actual) > 0
    ]
    modulos = await db.scalar(
        select(func.count())
        .select_from(ProgresoEducativo)
        .where(
            ProgresoEducativo.usuario_id == usuario.id,
            ProgresoEducativo.completado.is_(True),
        )
    )
    modulos_ok = int(modulos or 0)
    impulsivas = await db.scalar(
        select(func.count())
        .select_from(Transaccion)
        .where(
            Transaccion.iniciada_por_usuario_id == usuario.id,
            Transaccion.tipo == TipoTransaccion.COMPRA.value,
            Transaccion.forzada.is_(True),
            Transaccion.estado == EstadoTransaccion.COMPLETADA.value,
            Transaccion.created_at >= hace_30,
        )
    )
    impulsivas_n = int(impulsivas or 0)
    gastado_hoy = await _gastado_desde(db, cuenta.id, inicio_dia)
    gastado_semana = await _gastado_desde(db, cuenta.id, inicio_semana)

    positivos: list[ScoreFactor] = []
    negativos: list[ScoreFactor] = []
    consejos: list[str] = []
    puntaje = BASE

    if metas_con_abono:
        puntos = min(8 * len(metas_con_abono), MAX_METAS)
        puntaje += puntos
        positivos.append(
            ScoreFactor(
                codigo="metas_con_abono",
                etiqueta=f"{len(metas_con_abono)} meta(s) con dinero congelado",
                puntos=puntos,
            )
        )
    else:
        consejos.append("Crea una meta y abona aunque sea poco: el dinero congelado sube el score.")

    limite_semanal = cuenta.limite_gasto_semanal
    if limite_semanal is None and cuenta.limite_gasto_diario is not None:
        limite_semanal = Decimal(cuenta.limite_gasto_diario) * 7
    if limite_semanal is None or gastado_semana <= Decimal(limite_semanal):
        puntaje += 10
        positivos.append(
            ScoreFactor(
                codigo="bajo_limite_semanal",
                etiqueta="Compras de la semana dentro del límite",
                puntos=10,
            )
        )
    else:
        consejos.append("Esta semana ya pasaste el límite. Espera al lunes o pide un ajuste a tu acudiente.")

    if modulos_ok:
        puntos = min(8 * modulos_ok, MAX_EDUCACION)
        puntaje += puntos
        positivos.append(
            ScoreFactor(
                codigo="modulos_educativos",
                etiqueta=f"{modulos_ok} cápsula(s) de Academia BeHu",
                puntos=puntos,
            )
        )
    else:
        consejos.append("Completa una cápsula de Academia BeHu: cada quiz correcto suma al score.")

    if impulsivas_n:
        puntos = -min(12 * impulsivas_n, MAX_IMPULSO)
        puntaje += puntos
        negativos.append(
            ScoreFactor(
                codigo="compras_forzadas",
                etiqueta=f"{impulsivas_n} compra(s) confirmadas pese a la alerta",
                puntos=puntos,
            )
        )
        consejos.append("La próxima vez cancela la compra cuando BeHu Mini pida confirmación.")

    presupuesto = cuenta.limite_gasto_diario
    if presupuesto is not None and Decimal(presupuesto) > 0 and gastado_hoy >= Decimal(presupuesto) * Decimal("0.90"):
        puntaje -= 15
        negativos.append(
            ScoreFactor(
                codigo="presupuesto_dia",
                etiqueta="Hoy usaste más del 90% del límite diario",
                puntos=-15,
            )
        )
        consejos.append("Deja al menos un 10% del límite diario sin gastar.")

    puntaje = max(0, min(100, puntaje))
    nivel, color = _nivel(puntaje)
    if not consejos:
        consejos.append("Mantén abonos a metas y compras por debajo del límite semanal.")
    return ScoreResponse(
        puntaje=puntaje,
        nivel=nivel,
        color=color,
        factores_positivos=positivos,
        factores_negativos=negativos,
        consejos=consejos[:3],
    )
