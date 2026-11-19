"""Motor contextual BeHu Mini (sandbox, sin LLM externo)."""

import re
import unicodedata
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

TERMINOS_NO_PERTINENTES = (
    "recarga juego",
    "videojuegos",
    "discoteca",
    "apuesta",
    "casino",
    "cigarro",
    "cerveza",
    "licor",
    "skins",
    "vape",
    "bet",
    "bar",
)
TASA_CDT_MENSUAL = Decimal("0.01")


def _fold(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in base if not unicodedata.combining(ch)).lower()


def termino_no_pertinente(*partes: str | None) -> str | None:
    plano = _fold(" ".join(parte for parte in partes if parte))
    for termino in TERMINOS_NO_PERTINENTES:
        patron = _fold(termino)
        if " " in patron:
            if patron in plano:
                return termino
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(patron)}(?![a-z0-9])", plano):
            return termino
    return None


def proyectar_recuperable(principal: Decimal) -> tuple[Decimal, Decimal]:
    def futuro(meses: int) -> Decimal:
        return (principal * ((Decimal("1") + TASA_CDT_MENSUAL) ** meses)).quantize(Decimal("1"))

    return futuro(3), futuro(6)


def _principal_recuperable(compras: list[Transaccion]) -> tuple[Decimal, str]:
    from app.services.neobank_service import ids_hormiga

    hormiga = ids_hormiga(compras)
    vistos: set = set()
    total = Decimal("0")
    hay_vicio = False
    hay_hormiga = False
    for tx in compras:
        marca = termino_no_pertinente(tx.notas, tx.comercio, tx.descripcion, tx.categoria)
        if not marca and tx.id not in hormiga:
            continue
        if tx.id in vistos:
            continue
        vistos.add(tx.id)
        total += Decimal(tx.monto)
        hay_vicio = hay_vicio or bool(marca)
        hay_hormiga = hay_hormiga or tx.id in hormiga
    if hay_vicio and hay_hormiga:
        etiqueta = "gastos hormiga y no pertinentes"
    elif hay_vicio:
        etiqueta = "gastos no pertinentes"
    else:
        etiqueta = "gastos hormiga"
    return total, etiqueta


def _texto_recuperable(principal: Decimal, etiqueta: str) -> str | None:
    if principal <= 0:
        return None
    tres, seis = proyectar_recuperable(principal)
    return (
        f"Hay {principal:.0f} COP en {etiqueta}. "
        f"Si ese dinero se hubiera enviado a una meta o a un CDT al 1% mensual, "
        f"el monto recuperable sería {tres:.0f} COP a 3 meses y {seis:.0f} COP a 6 meses."
    )


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

    compras_nucleo = await _compras_para_consejo(db, usuario, cuenta.id, list(movimientos))
    principal, etiqueta = _principal_recuperable(compras_nucleo)
    aviso = _texto_recuperable(principal, etiqueta)
    if aviso:
        recomendaciones.insert(0, aviso)

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
        marcados = [
            (termino, tx)
            for tx in compras
            if (termino := termino_no_pertinente(tx.notas, tx.comercio, tx.descripcion, tx.categoria))
        ]
        if marcados:
            total = sum((Decimal(tx.monto) for _, tx in marcados), Decimal("0"))
            conceptos = ", ".join(dict.fromkeys(termino for termino, _ in marcados))
            alertas.append(
                ParentalAlert(
                    junior_id=str(junior_cuenta.id),
                    junior_nombre=nombre,
                    tipo="GASTO_NO_PERTINENTE",
                    mensaje=f"{nombre} registró «{conceptos}» por {total:.0f} COP.",
                    sugerencia=(
                        f"Sugerencia BeHu Mini: Redirigir estos ${total:.0f} COP hacia la meta activa "
                        "o activar el redondeo automático para compensar el impacto en el Score"
                    ),
                    severity="high",
                    badge="Gasto No Pertinente",
                )
            )
    return alertas


async def _compras_para_consejo(db: AsyncSession, usuario: Usuario, cuenta_id, propias: list[Transaccion]) -> list[Transaccion]:
    compras = [tx for tx in propias if tx.tipo == TipoTransaccion.COMPRA.value and tx.estado == "COMPLETADA"]
    if usuario.rol != "SENIOR":
        return compras
    from app.models.account import Cuenta
    from app.models.supervision import EstadoSupervision, SupervisionCuenta

    vinculos = (
        await db.scalars(
            select(SupervisionCuenta).where(
                SupervisionCuenta.cuenta_senior_id == cuenta_id,
                SupervisionCuenta.estado == EstadoSupervision.ACTIVA.value,
            )
        )
    ).all()
    for vinculo in vinculos:
        junior_cuenta = await db.get(Cuenta, vinculo.cuenta_junior_id)
        if junior_cuenta is None:
            continue
        extra = (
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
        compras.extend(extra)
    return compras


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
