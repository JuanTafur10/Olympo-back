from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class TicketBase(BaseModel):
    categoria: str = Field(..., description="Categoría del soporte")
    prioridad: str = Field(default="normal", description="Prioridad: normal, alta, urgente")
    canal: str = Field(default="chat", description="Canal preferido: chat, correo, telefono")
    asunto: str = Field(..., max_length=90)
    descripcion: str = Field(...)
    adjuntar_contexto: bool = True

class TicketCreate(TicketBase):
    pass

class TicketUpdate(BaseModel):
    prioridad: Optional[str] = None
    estado: Optional[str] = None
    asignado_a: Optional[str] = None  # user id of agent
    notas_internas: Optional[str] = None

class TicketInDB(TicketBase):
    id: str
    estado: str = Field(default="nuevo")
    creado_en: datetime = Field(default_factory=datetime.utcnow)
    actualizado_en: datetime = Field(default_factory=datetime.utcnow)
    asignado_a: Optional[str] = None
    notas_internas: Optional[str] = None
