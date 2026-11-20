"""Contrato JSON de Academia BeHu."""

from uuid import UUID

from pydantic import BaseModel, Field


class ModulePublic(BaseModel):
    id: UUID
    slug: str
    titulo: str
    resumen: str
    pregunta: str
    opciones: list[str]
    insignia: str
    orden: int
    categoria: str = "Finanzas"
    duracion_min: int = 2
    completado: bool
    insignia_obtenida: str | None = None


class CompleteModuleRequest(BaseModel):
    respuesta: str = Field(min_length=1, max_length=200)


class CompleteModuleResponse(BaseModel):
    modulo: ModulePublic
    correcto: bool
    ya_completado: bool
    mensaje: str
