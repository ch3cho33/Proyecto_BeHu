"""Cápsulas de micro-learning y quiz (HU-09)."""

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.education import ModuloEducativo, ProgresoEducativo
from app.models.user import Usuario
from app.schemas.education import CompleteModuleResponse, ModulePublic
from app.services.exceptions import ModuleNotFound, QuizAnswerIncorrect

CAPSULAS = [
    {
        "slug": "cdt-interes-compuesto",
        "titulo": "¿Qué es un CDT y el interés compuesto?",
        "resumen": (
            "Un CDT es un depósito a plazo en un banco vigilado en Colombia: dejas el dinero quieto "
            "y recibes intereses. Si esos intereses se reinvierten, ellos también generan intereses. "
            "Eso es interés compuesto, y crece más cuanto más tiempo dejas el capital."
        ),
        "pregunta": "Si los intereses de un CDT se reinvierten, ¿qué pasa?",
        "opciones": [
            "El capital deja de crecer",
            "Los intereses generan nuevos intereses",
            "El banco descuenta el saldo",
            "Solo aplica si el CDT está en dólares",
        ],
        "respuesta_correcta": "1",
        "insignia": "Semilla CDT",
        "orden": 1,
    },
    {
        "slug": "regla-50-30-20",
        "titulo": "Regla 50/30/20 para jóvenes",
        "resumen": (
            "Una forma simple de partir el dinero que recibes: 50% necesidades (transporte, comida), "
            "30% gustos (salidas, ropa) y 20% ahorro o metas. El 20% es el que BeHu puede congelar "
            "para que no se vaya en compras del día."
        ),
        "pregunta": "En la regla 50/30/20, el 20% se destina a…",
        "opciones": ["Entretenimiento", "Ahorro y metas", "Solo comida", "Ropa de temporada"],
        "respuesta_correcta": "1",
        "insignia": "Brújula 50/30/20",
        "orden": 2,
    },
    {
        "slug": "gasto-hormiga",
        "titulo": "Cómo evitar el gasto hormiga",
        "resumen": (
            "El gasto hormiga es pequeño y se repite: el snack, el domicilio, el juego de un dólar. "
            "Uno solo no duele; treinta sí vacían la semana. Anótalo, ponle un tope y pasa lo que "
            "sobre a una meta."
        ),
        "pregunta": "Un gasto hormiga es…",
        "opciones": [
            "Una compra grande una vez al año",
            "Pequeños gastos frecuentes que suman mucho",
            "El abono a una meta de ahorro",
            "Un CDT a 90 días",
        ],
        "respuesta_correcta": "1",
        "insignia": "Lupa hormiga",
        "orden": 3,
    },
    {
        "slug": "ahorro-visual",
        "titulo": "Metas de ahorro con seguimiento visual",
        "resumen": "Una meta visible congela el dinero antes de que se vaya en la siguiente compra. El avance se lee en porcentaje, no en intenciones.",
        "pregunta": "¿Qué hace una meta activa en BeHu?",
        "opciones": ["Aumenta el límite diario", "Apare el ahorro fuera del gasto", "Convierte el saldo a dólares", "Borra los movimientos"],
        "respuesta_correcta": "1",
        "insignia": "Ahorrador Pro",
        "orden": 4,
    },
]


async def asegurar_modulos(db: AsyncSession) -> None:
    existentes = set((await db.scalars(select(ModuloEducativo.slug))).all())
    for capsula in CAPSULAS:
        if capsula["slug"] in existentes:
            continue
        db.add(
            ModuloEducativo(
                slug=capsula["slug"],
                titulo=capsula["titulo"],
                resumen=capsula["resumen"],
                pregunta=capsula["pregunta"],
                opciones_json=json.dumps(capsula["opciones"], ensure_ascii=False),
                respuesta_correcta=capsula["respuesta_correcta"],
                insignia=capsula["insignia"],
                orden=capsula["orden"],
            )
        )
    await db.commit()


def _normalizar(respuesta: str, opciones: list[str], correcta: str) -> bool:
    limpia = respuesta.strip().lower()
    if limpia == correcta.strip().lower():
        return True
    if limpia in {"a", "b", "c", "d"}:
        indice = ord(limpia) - ord("a")
        return str(indice) == correcta
    try:
        return opciones[int(correcta)].strip().lower() == limpia
    except (ValueError, IndexError):
        return False


PRESENTACION = {
    "cdt-interes-compuesto": ("Inversión", 3, "Inversionista Novato"),
    "regla-50-30-20": ("Presupuesto", 2, "Maestro del Presupuesto"),
    "gasto-hormiga": ("Hábitos", 2, "Escudo Financiero"),
    "ahorro-visual": ("Metas", 3, "Ahorrador Pro"),
}


def _publico(modulo: ModuloEducativo, progreso: ProgresoEducativo | None) -> ModulePublic:
    categoria, minutos, insignia = PRESENTACION.get(modulo.slug, ("Finanzas", 2, modulo.insignia))
    return ModulePublic(
        id=modulo.id,
        slug=modulo.slug,
        titulo=modulo.titulo,
        resumen=modulo.resumen,
        pregunta=modulo.pregunta,
        opciones=json.loads(modulo.opciones_json),
        insignia=insignia,
        orden=modulo.orden,
        categoria=categoria,
        duracion_min=minutos,
        completado=progreso is not None and progreso.completado,
        insignia_obtenida=progreso.insignia if progreso else None,
    )


async def listar_modulos(db: AsyncSession, usuario: Usuario) -> list[ModulePublic]:
    await asegurar_modulos(db)
    modulos = (
        await db.scalars(select(ModuloEducativo).order_by(ModuloEducativo.orden))
    ).all()
    progresos = (
        await db.scalars(
            select(ProgresoEducativo).where(ProgresoEducativo.usuario_id == usuario.id)
        )
    ).all()
    por_modulo = {item.modulo_id: item for item in progresos}
    return [_publico(modulo, por_modulo.get(modulo.id)) for modulo in modulos]


async def completar_modulo(
    db: AsyncSession,
    usuario: Usuario,
    modulo_id: UUID,
    respuesta: str,
) -> CompleteModuleResponse:
    await asegurar_modulos(db)
    modulo = await db.get(ModuloEducativo, modulo_id)
    if modulo is None:
        raise ModuleNotFound("Módulo educativo no encontrado")
    previo = await db.scalar(
        select(ProgresoEducativo).where(
            ProgresoEducativo.usuario_id == usuario.id,
            ProgresoEducativo.modulo_id == modulo.id,
        )
    )
    if previo is not None and previo.completado:
        return CompleteModuleResponse(
            modulo=_publico(modulo, previo),
            correcto=True,
            ya_completado=True,
            mensaje=f"Ya tienes la insignia {previo.insignia}.",
        )
    opciones = json.loads(modulo.opciones_json)
    if not _normalizar(respuesta, opciones, modulo.respuesta_correcta):
        raise QuizAnswerIncorrect("Respuesta incorrecta. Lee la cápsula e inténtalo de nuevo.")
    progreso = ProgresoEducativo(
        usuario_id=usuario.id,
        modulo_id=modulo.id,
        completado=True,
        insignia=modulo.insignia,
        respondido_en=datetime.now(timezone.utc),
    )
    db.add(progreso)
    await db.commit()
    await db.refresh(progreso)
    return CompleteModuleResponse(
        modulo=_publico(modulo, progreso),
        correcto=True,
        ya_completado=False,
        mensaje=f"Quiz correcto. Ganaste la insignia {modulo.insignia}.",
    )
