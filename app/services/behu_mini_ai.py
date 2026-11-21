"""Motor contextual BeHu Mini (sandbox, sin LLM externo)."""

import logging
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
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

logger = logging.getLogger("behu.mini")

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
TASA_CDT_MENSUAL = 0.01


def _f(valor) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _instante(valor: datetime | None) -> datetime:
    if valor is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


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
    base = _f(principal)

    def futuro(meses: int) -> Decimal:
        return Decimal(str(round(base * ((1 + TASA_CDT_MENSUAL) ** meses))))

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
        total += Decimal(str(_f(tx.monto)))
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
        objetivo = _f(meta.monto_objetivo)
        avance = (_f(meta.monto_actual) / objetivo * 100) if objetivo else 0.0
        limite = meta.fecha_limite.isoformat() if meta.fecha_limite else "sin fecha"
        consejos.append(
            f"Meta «{meta.nombre}»: llevas {avance:.0f}%. "
            f"Congelar un abono pequeño hoy deja ese dinero fuera de las compras impulsivas. "
            f"Fecha límite {limite}."
        )
    if _f(saldo) < 20000:
        consejos.append("Tu saldo disponible es bajo. Pide a tu acudiente un ajuste de presupuesto antes de una compra grande.")
    if not consejos:
        consejos.append("Vas bien: mantén las compras por debajo del 40% de tu saldo.")
    return consejos[:4]


def _consejo_senior(saldo: Decimal, juniors: int) -> list[str]:
    consejos = [
        "Separa el gasto familiar del excedente. Lo que no se va a presupuestos Junior puede trabajar en el mes.",
    ]
    if _f(saldo) >= 500000:
        consejos.append(
            "Con este excedente en COP, un CDT a 90 o 180 días en un banco vigilado por la Superfinanciera "
            "es una opción de bajo movimiento para el colchón familiar."
        )
    if _f(saldo) >= 2000000:
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


async def respuesta_de_respaldo(db: AsyncSession, usuario: Usuario) -> AiConsultResponse:
    moneda = usuario.moneda_preferida or "COP"
    limite = 0.0
    puntaje = "sin dato"
    try:
        cuenta = await get_cuenta_usuario(db, usuario)
        limite = _f(cuenta.limite_gasto_diario)
    except Exception:
        logger.warning("BeHu Mini no leyó el límite diario", exc_info=True)
    try:
        from app.services.scoring_service import calcular_score

        puntaje = str((await calcular_score(db, usuario)).puntaje)
    except Exception:
        logger.warning("BeHu Mini no leyó el Score", exc_info=True)
    texto = (
        f"Hola {usuario.nombres}. Tu moneda es {moneda} y tu Score es {puntaje}/100. "
        f"Límite diario {limite:.0f} {moneda}. "
        "Gasta solo lo que quede después de apartar la meta de esta semana."
    )
    ahora = datetime.now(timezone.utc).isoformat()
    return AiConsultResponse(
        id="respaldo",
        rol=usuario.rol,
        enfoque="respaldo",
        resumen=texto,
        recomendaciones=[texto],
        fuente="local",
        created_at=ahora,
        reply=texto,
        response=texto,
        insights=[texto],
        suggested_actions=["Revisa tu saldo en Inicio y aparta un abono a la meta."],
    )


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
    congelado = Decimal(str(_f(cuadro.get("saldo_congelado"))))
    saldo = Decimal(str(_f(saldo)))
    recomendaciones.append(
        f"Saldo líquido {saldo:.0f} {cuenta.moneda} y saldo congelado en metas {congelado:.0f}. "
        f"Regla 50/30/20 sobre ingresos de {cuadro['ingresos']}: "
        f"necesidades {cuadro['necesidades']['real']} de {cuadro['necesidades']['objetivo']}, "
        f"deseos {cuadro['deseos']['real']} de {cuadro['deseos']['objetivo']}, "
        f"ahorro {cuadro['ahorro']['real']} de {cuadro['ahorro']['objetivo']}."
    )
    if usuario.rol == "JUNIOR":
        abono = max(5000.0, round(_f(saldo) * 0.10))
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
    recomendaciones[0:0] = await _lineas_intencion(
        db,
        usuario,
        pregunta,
        saldo,
        congelado,
        cuenta.moneda,
        metas,
        compras_nucleo,
        cuadro,
    )
    recomendaciones.insert(0, f"Hola. Tu saldo disponible es {saldo:.2f} {cuenta.moneda}.")

    contexto = {
        "saldo": f"{_f(saldo):.2f}",
        "moneda": cuenta.moneda,
        "compras_recientes": sum(categorias.values()),
        "categorias": dict(categorias),
        "metas_activas": sum(1 for meta in metas if meta.estado == EstadoMeta.ACTIVA.value),
        "pregunta": pregunta,
        "juniors_vinculados": juniors_vinculados,
    }
    documento = {"_id": "local", "created_at": datetime.now(timezone.utc).isoformat()}
    fuente = "local"
    try:
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
    except Exception:
        logger.warning("BeHu Mini no pudo guardar la consulta", exc_info=True)
    reply = "\n".join(f"• {linea}" for linea in recomendaciones)
    return AiConsultResponse(
        id=documento["_id"],
        rol=usuario.rol,
        enfoque=enfoque,
        resumen=recomendaciones[0],
        recomendaciones=recomendaciones,
        fuente=fuente,
        created_at=str(documento.get("created_at") or datetime.now(timezone.utc).isoformat()),
        reply=reply,
        response=reply,
        insights=recomendaciones[:4],
        suggested_actions=recomendaciones[-2:],
    )


def _intenciones(pregunta: str | None) -> set[str]:
    texto = _fold(pregunta or "")
    halladas: set[str] = set()
    if any(clave in texto for clave in ("invert", "cdt", "excedent", "rendim")):
        halladas.add("inversion")
    if any(clave in texto for clave in ("ahorr", "meta", "gastar", "puedo gastar", "cuanto puedo")):
        halladas.add("ahorro")
    if any(clave in texto for clave in ("hormiga", "vicio", "pertinente", "diagnost", "fuga")):
        halladas.add("diagnostico")
    if any(clave in texto for clave in ("familiar", "junior", "mesada", "hijo", "dependiente", "parental")):
        halladas.add("familiar")
    if not halladas:
        halladas.add("fallback")
    return halladas


async def _lineas_intencion(
    db: AsyncSession,
    usuario: Usuario,
    pregunta: str | None,
    saldo: Decimal,
    congelado: Decimal,
    moneda: str,
    metas: list[MetaAhorro],
    compras: list[Transaccion],
    cuadro: dict,
) -> list[str]:
    hoy = datetime.now(timezone.utc).date()
    if hoy.month == 12:
        fin_mes = hoy.replace(day=31)
    else:
        fin_mes = hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)
    dias = max(1, (fin_mes - hoy).days + 1)
    gastos = sum(_f(tx.monto) for tx in compras if tx.tipo == TipoTransaccion.COMPRA.value)
    ingresos = _f(cuadro.get("ingresos"))
    saldo_num = _f(saldo)
    congelado_num = _f(congelado)
    emergencia = round(gastos * 3)
    invertible = max(0.0, round(saldo_num - emergencia))
    lineas: list[str] = []
    for intencion in _intenciones(pregunta):
        if intencion == "inversion":
            tres, seis = proyectar_recuperable(Decimal(str(invertible)))
            doce = round(invertible * ((1 + TASA_CDT_MENSUAL) ** 12))
            lineas.append(
                f"Puedes invertir hoy {invertible:.0f} {moneda} sin tocar el fondo de emergencia "
                f"de 3 meses de gastos ({emergencia:.0f} {moneda}). "
                f"A un CDT del 1% mensual ese capital llega a {tres:.0f} en 3 meses, {seis:.0f} en 6 y {doce:.0f} en 12."
            )
        elif intencion == "ahorro":
            diaria = round(saldo_num / dias) if dias else 0.0
            lineas.append(
                f"Tu capacidad diaria segura es {diaria:.0f} {moneda} durante los {dias} días que faltan del mes."
            )
            for meta in metas:
                if meta.estado != EstadoMeta.ACTIVA.value:
                    continue
                falta = max(0.0, _f(meta.monto_objetivo) - _f(meta.monto_actual))
                lineas.append(f"A la meta «{meta.nombre}» le faltan {falta:.0f} {moneda}.")
        elif intencion == "diagnostico":
            fugas = []
            for tx in compras:
                termino = termino_no_pertinente(tx.notas, tx.comercio, tx.descripcion, tx.categoria)
                if termino:
                    fugas.append(f"{termino} {_f(tx.monto):.0f} {moneda}")
            from app.services.neobank_service import ids_hormiga

            if ids_hormiga(compras):
                hormiga = sum(_f(tx.monto) for tx in compras if tx.id in ids_hormiga(compras))
                fugas.append(f"hormiga {hormiga:.0f} {moneda}")
            detalle = ", ".join(fugas) if fugas else "no hay fugas con nombre en los movimientos recientes"
            lineas.append(
                f"Fugas recientes: {detalle}. Plan de recorte: congela ese monto en la meta activa y baja el tope de ocio esta semana."
            )
        elif intencion == "familiar" and usuario.rol == "SENIOR":
            alertas = await alertas_parentales(db, usuario)
            if not alertas:
                lineas.append("Ningún Junior vinculado tiene alertas abiertas. La mesada puede mantenerse.")
            else:
                for alerta in alertas:
                    lineas.append(f"{alerta.junior_nombre}: {alerta.tipo}. {alerta.sugerencia}")
        else:
            ratio = round(gastos / ingresos, 2) if ingresos else 0.0
            lineas.append(
                f"Diagnóstico ejecutivo: liquidez {saldo_num:.0f} {moneda}, ahorro reservado {congelado_num:.0f} {moneda}, "
                f"ratio gasto/ingreso {ratio}. Acciones: 1) aparta un abono a la meta activa. "
                f"2) revisa el bucket 50/30/20 que más se pasó este mes."
            )
    return lineas


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
            total = sum((_f(tx.monto) for _, tx in marcados), 0.0)
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
