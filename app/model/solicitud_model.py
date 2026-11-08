from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SolicitudInversionBase(BaseModel):
    proyecto_id: str
    inversionista_id: str
    monto_solicitado: float = Field(..., gt=0, description="Monto solicitado debe ser mayor a 0")
    propuesta: Optional[str] = None


class SolicitudInversionCreate(SolicitudInversionBase):
    pass


class SolicitudInversionUpdate(BaseModel):
    estado: Optional[str] = None
    propuesta: Optional[str] = None


class SolicitudInversionResponse(SolicitudInversionBase):
    id: str
    estado: str
    creada_en: datetime
    actualizada_en: datetime

    class Config:
        from_attributes = True


class ListarSolicitudesResponse(BaseModel):
    ok: bool
    solicitudes: list[dict] = []
    mensaje: Optional[str] = None


class CrearSolicitudResponse(BaseModel):
    ok: bool
    solicitud_id: Optional[str] = None
    mensaje: Optional[str] = None


class ActualizarSolicitudResponse(BaseModel):
    ok: bool
    mensaje: Optional[str] = None
