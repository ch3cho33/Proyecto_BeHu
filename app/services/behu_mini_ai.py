"""Motor contextual BeHu Mini (sandbox, sin LLM externo)."""

from collections import Counter
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import EstadoMeta, MetaAhorro
from app.models.transaction import TipoTransaccion, Transaccion
from app.models.user import Usuario
from app.schemas.ai import AiConsultResponse, AiHistoryItem
from app.services.account_service import get_cuenta_usuario
from app.services.ai_store import guardar_habito, guardar_recomendacion, historial
from app.services.ledger_service import saldo_desde_ledger


def _consejo_junior(saldo: Decimal, categorias: Counter, metas: list[MetaAhorro]) -> list[str]:
    consejos: list[str] = []
    if categorias:
        top, veces = categorias.most_common(1)[0]
        consejos.append(
            f"Tu categoría más frecuente es {top} ({veces} compras). "
            "Prueba un tope semanal para esa categoría antes de abrir la app del comercio."
        )
        if top in {"COMIDA", "ENTRETENIMIENTO"} and veces >= 2:
            consejos.append(
                "Hay un patrón de gastos hormiga. Un café o un snack diario se come el mes: "
                "junta esos montos y pásalos a una meta."
            )
    else:
        consejos.append("Todavía no registras compras. Cuando gastes, BeHu Mini te dirá en qué se va el dinero.")
    for meta in metas:
        if meta.estado != EstadoMeta.ACTIVA.value:
            continue
        avance = (Decimal(meta.monto_actual) / Decimal(meta.monto_objetivo) * 100) if meta.monto_objetivo else 0
        consejos.append(
            f"Meta «{meta.nombre}»: llevas {avance:.0f}%. "
            f"Congelar un abono pequeño hoy deja ese dinero fuera de las compras impulsivas. "
            f"Fecha límite {meta.fecha_limite.isoformat()}."
        )
    if saldo < Decimal("20000"):
        consejos.append("Tu saldo disponible es bajo. Pide a tu acudiente un ajuste de presupuesto antes de una compra grande.")
    if not consejos:
        consejos.append("Vas bien: mantén las compras por debajo del 40% de tu saldo.")
    return consejos[:4]


def _consejo_senior(saldo: Decimal, juniors: int) -> list[str]:
    consejos = [
        "Separa el gasto familiar del excedente. Lo que no se va a presupuestos Junior puede trabajar en el mes.",
    ]
    if saldo >= Decimal("500000"):
        consejos.append(
            "Con este excedente en COP, un CDT a 90 o 180 días en un banco vigilado por la Superfinanciera "
            "es una opción de bajo movimiento para el colchón familiar."
        )
    if saldo >= Decimal("2000000"):
        consejos.append(
            "El excedente ya justifica diversificar: un fondo de inversión colectiva conservador "
            "(renta fija de corto plazo) más el CDT, sin concentrar todo en un solo emisor."
        )
    else:
        consejos.append(
            "Mientras el excedente crece, prioriza liquidez: cuenta de ahorros remunerada y un CDT corto, "
            "antes que un fondo con permanencia larga."
        )
    if juniors:
        consejos.append(
            f"Tienes {juniors} cuenta(s) Junior activa(s). Revisa si el presupuesto periódico cubre "
            "educación y transporte antes de mover excedente a inversión."
        )
    return consejos[:4]


async def consultar(db: AsyncSession, usuario: Usuario, pregunta: str | None) -> AiConsultResponse:
    cuenta = await get_cuenta_usuario(db, usuario)
    saldo = await saldo_desde_ledger(db, cuenta.id)
    movimientos = (
        await db.scalars(
            select(Transaccion)
            .where(Transaccion.iniciada_por_usuario_id == usuario.id)
            .order_by(Transaccion.created_at.desc())
            .limit(30)
        )
    ).all()
    categorias = Counter(
        tx.categoria for tx in movimientos if tx.tipo == TipoTransaccion.COMPRA.value and tx.categoria
    )
    metas = list(
        (
            await db.scalars(select(MetaAhorro).where(MetaAhorro.cuenta_id == cuenta.id))
        ).all()
    )
    juniors_vinculados: int | None = None
    if usuario.rol == "JUNIOR":
        recomendaciones = _consejo_junior(saldo, categorias, metas)
        enfoque = "habitos_y_metas"
    else:
        from app.models.supervision import EstadoSupervision, SupervisionCuenta

        activos = (
            await db.scalars(
                select(SupervisionCuenta).where(
                    SupervisionCuenta.cuenta_senior_id == cuenta.id,
                    SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
                )
            )
        ).all()
        juniors_vinculados = len(activos)
        recomendaciones = _consejo_senior(saldo, juniors_vinculados)
        enfoque = "excedente_familiar_colombia"

    from app.services.neobank_service import resumen_503020

    cuadro = await resumen_503020(db, usuario)
    congelado = Decimal(cuadro["saldo_congelado"])
    recomendaciones.append(
        f"Saldo líquido {saldo:.0f} {cuenta.moneda} y saldo congelado en metas {congelado:.0f}. "
        f"Regla 50/30/20 sobre ingresos de {cuadro['ingresos']}: "
        f"necesidades {cuadro['necesidades']['real']} de {cuadro['necesidades']['objetivo']}, "
        f"deseos {cuadro['deseos']['real']} de {cuadro['deseos']['objetivo']}, "
        f"ahorro {cuadro['ahorro']['real']} de {cuadro['ahorro']['objetivo']}."
    )
    if usuario.rol == "JUNIOR":
        abono = max(Decimal("5000"), (saldo * Decimal("0.10")).quantize(Decimal("1")))
        recomendaciones.append(
            f"Reto de ahorro: abona {abono:.0f} {cuenta.moneda} a tu meta activa. "
            "Si ves suscripciones o gastos hormiga de comida y ocio, congela ese monto antes de la próxima compra."
        )
    else:
        recomendaciones.append(
            "Fondo de emergencia: reserva de 3 a 6 meses de gastos del hogar. "
            "El excedente que quede después de esa reserva puede ir a un CDT o a un fondo conservador de renta fija."
        )

    contexto = {
        "saldo": f"{saldo:.2f}",
        "moneda": cuenta.moneda,
        "compras_recientes": sum(categorias.values()),
        "categorias": dict(categorias),
        "metas_activas": sum(1 for meta in metas if meta.estado == EstadoMeta.ACTIVA.value),
        "pregunta": pregunta,
        "juniors_vinculados": juniors_vinculados,
    }
    await guardar_habito(
        {
            "usuario_id": str(usuario.id),
            "cuenta_id": str(cuenta.id),
            "evento": "consulta_behu_mini",
            "payload": contexto,
        }
    )
    documento, fuente = await guardar_recomendacion(
        {
            "usuario_id": str(usuario.id),
            "cuenta_id": str(cuenta.id),
            "modelo": "behu-mini-rules",
            "rol": usuario.rol,
            "enfoque": enfoque,
            "recomendaciones": recomendaciones,
            "contexto": contexto,
            "aceptada": None,
        }
    )
    return AiConsultResponse(
        id=documento["_id"],
        rol=usuario.rol,
        enfoque=enfoque,
        resumen=recomendaciones[0],
        recomendaciones=recomendaciones,
        fuente=fuente,
        created_at=documento["created_at"],
    )


async def alertas_parentales(db: AsyncSession, usuario: Usuario) -> list:
    from app.schemas.ai import ParentalAlert
    from app.models.supervision import EstadoSupervision, SupervisionCuenta
    from app.services.account_service import get_cuenta_usuario
    from app.services.neobank_service import ids_hormiga

    if usuario.rol != "SENIOR":
        return []
    cuenta = await get_cuenta_usuario(db, usuario)
    vinculos = (
        await db.scalars(
            select(SupervisionCuenta).where(
                SupervisionCuenta.cuenta_senior_id == cuenta.id,
                SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
            )
        )
    ).all()
    alertas: list[ParentalAlert] = []
    for vinculo in vinculos:
        from app.models.account import Cuenta

        junior_cuenta = await db.get(Cuenta, vinculo.cuenta_junior_id)
        if junior_cuenta is None:
            continue
        junior = await db.get(Usuario, junior_cuenta.usuario_id)
        nombre = f"{junior.nombres} {junior.apellidos}".strip() if junior else "Junior"
        compras = list(
            (
                await db.scalars(
                    select(Transaccion)
                    .where(
                        Transaccion.iniciada_por_usuario_id == junior_cuenta.usuario_id,
                        Transaccion.tipo == TipoTransaccion.COMPRA.value,
                        Transaccion.estado == "COMPLETADA",
                    )
                    .order_by(Transaccion.created_at.desc())
                    .limit(40)
                )
            ).all()
        )
        if ids_hormiga(compras):
            alertas.append(
                ParentalAlert(
                    junior_id=str(junior_cuenta.id),
                    junior_nombre=nombre,
                    tipo="GASTO_HORMIGA",
                    mensaje=f"{nombre} acumula compras pequeñas de comida u ocio en menos de 48 horas.",
                    sugerencia="Baja el límite diario o creen una meta conjunta para apartar ese monto.",
                )
            )
        if any(tx.is_impulsive or tx.forzada for tx in compras):
            alertas.append(
                ParentalAlert(
                    junior_id=str(junior_cuenta.id),
                    junior_nombre=nombre,
                    tipo="GASTO_IMPULSIVO",
                    mensaje=f"{nombre} confirmó al menos una compra que BeHu Mini había frenado.",
                    sugerencia="Revisa el movimiento y, si se repite, bloquea la tarjeta desde Gestión familiar.",
                )
            )
    return alertas


async def listar_historial(usuario: Usuario) -> list[AiHistoryItem]:
    docs, _fuente = await historial(str(usuario.id))
    return [
        AiHistoryItem(
            id=str(doc.get("_id")),
            rol=doc.get("rol", usuario.rol),
            enfoque=doc.get("enfoque", ""),
            recomendaciones=list(doc.get("recomendaciones") or []),
            created_at=doc.get("created_at", ""),
        )
        for doc in docs
    ]
