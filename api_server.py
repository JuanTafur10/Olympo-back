from datetime import datetime, timezone
from uuid import UUID
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.controller.usuario_controller import Usuario_controller
from app.controller.proyecto_controller import Proyecto_controller
from app.controller.solicitud_controller import (
    crear_solicitud_inversion,
    listar_solicitudes_por_proyecto,
    listar_solicitudes_por_inversionista,
    obtener_solicitud,
    actualizar_estado_solicitud,
    eliminar_solicitud,
)
from app.model.usuario_model import Usuario
from app.model.solicitud_model import (
    SolicitudInversionCreate,
    SolicitudInversionUpdate,
    SolicitudInversionResponse,
    ListarSolicitudesResponse,
    CrearSolicitudResponse,
    ActualizarSolicitudResponse,
)
from app.model.groq_model import IAAsistente
from app.core.firebase_conection import admin_auth, firestore_db
from app.core.notificaciones_firestore import (
    crear_notificacion_usuario,
    eliminar_notificacion,
    listar_notificaciones_usuario,
    marcar_notificacion_leida,
    marcar_todas_notificaciones_leidas,
)
from app.core.tickets_firestore import sincronizar_ticket_firestore, sincronizar_tickets_firestore
from app.core.cloudinary_config import subir_imagen
from app.core import sendgrid_service
import os
import requests
from app.model.ticket_model import TicketCreate, TicketUpdate
from app.controller.ticket_controller import crear_ticket, listar_tickets, obtener_ticket, actualizar_ticket
from app.controller.ares_cache_controller import (
    obtener_riesgos_detectados_ares,
    guardar_riesgos_detectados_ares,
    listar_riesgos_personalizados_ares,
    crear_riesgo_personalizado_ares,
    eliminar_riesgo_personalizado_ares,
)

app = FastAPI(title="Olympo API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def log_email_configuration():
    email_status = sendgrid_service.get_sendgrid_status()
    if email_status.get("configured"):
        print(
            "[Email] SendGrid configurado: "
            f"from={email_status.get('from_email')} "
            f"name={email_status.get('from_name')} "
            f"api_key_suffix={email_status.get('api_key_suffix')}"
        )
    else:
        print("[Email] SendGrid no configurado en este entorno")


class LoginRequest(BaseModel):
    email: str
    password: str
    tipo_usuario: str | None = None


class RegistroRequest(BaseModel):
    tipo_usuario: str
    nombre_usuario: str
    nombre: str | None = None
    email: str
    password: str
    confirm_password: str
    telefono: str | None = None
    website: str | None = None
    linkedin: str | None = None
    ciudad: str | None = None
    descripcion: str | None = None
    acepta_terminos: bool = False
    biografia: str | None = None
    licencias_certificaciones: list[str] | None = None
    intereses_inversion: list[str] | None = None
    monto_disponible: float | None = None


class AdminRegistroRequest(BaseModel):
    nombre_usuario: str
    nombre: str | None = None
    email: str
    password: str
    confirm_password: str
    telefono: str | None = None
    website: str | None = None
    linkedin: str | None = None
    ciudad: str | None = None
    descripcion: str | None = None
    biografia: str | None = None
    acepta_terminos: bool = True


class EstadoUsuarioRequest(BaseModel):
    activo: bool


class EstadoRegistroRequest(BaseModel):
    registro_libre: bool


class BootstrapAdminRequest(BaseModel):
    bootstrap_secret: str
    nombre_usuario: str
    nombre: str | None = None
    email: str
    password: str
    confirm_password: str
    telefono: str | None = None
    website: str | None = None
    linkedin: str | None = None
    ciudad: str | None = None
    descripcion: str | None = None
    biografia: str | None = None
    acepta_terminos: bool = True


class ChatbotRequest(BaseModel):
    mensaje: str
    usuario_id: str | None = None


class RiesgoPersonalizadoRequest(BaseModel):
    proyecto_id: str
    usuario_id: str
    nombre: str
    categoria: str | None = None
    descripcion: str | None = None
    tratamiento: str | None = None
    probabilidad: int
    impacto: int


class ChatMensajeRequest(BaseModel):
    chat_id: str
    sender_id: str
    sender_name: str
    sender_photo: str | None = None
    receiver_id: str
    receiver_name: str
    receiver_photo: str | None = None
    texto: str
    tipo_mensaje: str | None = None
    meeting_url: str | None = None
    meeting_title: str | None = None
    meeting_start: str | None = None
    meeting_end: str | None = None
    meeting_details: str | None = None


class MarcarLeidosRequest(BaseModel):
    chat_id: str
    receiver_id: str


class PerfilUsuarioRequest(BaseModel):
    telefono: str | None = None
    website: str | None = None
    linkedin: str | None = None
    ciudad: str | None = None
    descripcion: str | None = None


class ProyectoRequest(BaseModel):
    propietario_id: str
    propietario_email: str | None = None
    titulo: str
    descripcion: str | None = None
    presupuesto: float = 0
    estado: str = "activo"
    fecha_publicacion: str | None = None


class OptimizarRequest(BaseModel):
    titulo: str
    descripcion: str


class NotificacionesRequest(BaseModel):
    usuario_id: str


class CrearNotificacionRequest(BaseModel):
    usuario_id: str
    tipo: str
    titulo: str
    mensaje: str | None = None
    ruta_destino: str | None = None
    metadata: dict | None = None


def _obtener_token_bearer(request: Request) -> str:
    authorization = (request.headers.get("Authorization") or "").strip()
    if not authorization.lower().startswith("bearer "):
        raise ValueError("Se requiere autenticación con token Bearer")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise ValueError("Se requiere autenticación con token Bearer")

    return token


def _obtener_usuario_autenticado(request: Request, requiere_admin: bool = False):
    token = _obtener_token_bearer(request)

    try:
        token_decodificado = admin_auth.verify_id_token(token)
    except Exception as error:
        raise ValueError("Token inválido o expirado") from error

    firebase_uid = (
        token_decodificado.get("uid")
        or token_decodificado.get("user_id")
        or token_decodificado.get("sub")
    )

    if not firebase_uid:
        raise ValueError("Token inválido")

    usuario = Usuario_controller.obtener_datos_usuario(firebase_uid)
    if not usuario:
        raise ValueError("Usuario no encontrado")

    if not usuario.get("activo", True):
        raise ValueError("La cuenta está desactivada")

    if requiere_admin and str(usuario.get("rol") or "").lower() != "admin":
        raise ValueError("Se requieren permisos de administrador")

    return usuario


def _obtener_bootstrap_secret() -> str:
    return (os.getenv("OLYMPO_BOOTSTRAP_ADMIN_SECRET") or "").strip()


def generar_score_automatico(proyecto_id: str):
    """Tarea en segundo plano para generar el scoring de la IA."""
    try:
        print(f"[Auto-Scoring] Iniciando análisis para proyecto: {proyecto_id}")
        
        # Obtener datos del proyecto para saber quién es el dueño
        proyecto = Proyecto_controller.obtener_proyecto(proyecto_id)
        if not proyecto:
            print(f"[Auto-Scoring] Error: Proyecto {proyecto_id} no encontrado.")
            return

        analisis = IAAsistente.score_bot(proyecto_id)
        
        if not analisis.startswith("Error"):
            Proyecto_controller.actualizar_analisis_ai(proyecto_id, analisis)
            print(f"[Auto-Scoring] Análisis completado y guardado para: {proyecto_id}")
            
            # Enviar notificación al dueño del proyecto
            try:
                crear_notificacion_usuario(
                    usuario_id=proyecto["propietario_id"],
                    tipo="ia_scoring",
                    titulo="¡Análisis IA listo!",
                    mensaje=f"La IA ha terminado de evaluar tu proyecto '{proyecto['titulo']}'. Ya puedes ver el scoring.",
                    ruta_destino="proyectos",
                    metadata={"proyecto_id": proyecto_id}
                )
            except Exception as e:
                print(f"[Auto-Scoring] Error al enviar notificación: {e}")
        else:
            print(f"[Auto-Scoring] Error de la IA: {analisis}")
    except Exception as e:
        print(f"[Auto-Scoring] Excepción: {e}")


@app.get("/api/v1/usuarios")
def listar_usuarios(excluir_usuario_id: str | None = None):
    try:
        usuarios = Usuario_controller.listar_usuarios(excluir_usuario_id=excluir_usuario_id)
        return {"ok": True, "usuarios": usuarios}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.get("/api/v1/health")
def health_check():
    return {"ok": True, "servicio": "backend-olympo"}


@app.get("/api/v1/email/config")
def email_config():
    return {"ok": True, "sendgrid": sendgrid_service.get_sendgrid_status()}


@app.post("/api/v1/email/test")
def email_test(payload: dict):
    """Enviar un correo de prueba inmediato.

    Body JSON esperado: {"to": "destinatario@dominio", "name": "Nombre Opcional"}
    Devuelve ok: True si el envío fue aceptado por la librería, False en otro caso.
    """
    try:
        to = (payload.get("to") if isinstance(payload, dict) else None) or ""
        name = (payload.get("name") if isinstance(payload, dict) else None) or "Usuario de prueba"
        to = str(to).strip()
        if not to:
            return {"ok": False, "mensaje": "Campo 'to' requerido en JSON"}

        # Intentar enviar el correo de bienvenida como prueba
        result = sendgrid_service.send_welcome_email(to, name)
        # Si el servicio devolvió un dict con detalles, retonarlo para diagnóstico
        if isinstance(result, dict):
            return {"ok": result.get("ok", False), "detalle": result}
        if result:
            return {"ok": True, "mensaje": "Correo enviado (aceptado por API)"}
        else:
            return {"ok": False, "mensaje": "No se pudo enviar el correo (ver logs)"}
    except Exception as e:
        return {"ok": False, "mensaje": f"Excepción: {str(e)}"}


@app.get("/api/v1/proyectos")
def listar_proyectos(propietario_id: str | None = None, propietario_email: str | None = None, inversionista_id: str | None = None):
    try:
        propietario_resuelto = None
        inversionista_resuelto = None

        if propietario_id:
            try:
                UUID(propietario_id)
                usuario_existente = Usuario_controller.obtener_datos_usuario(propietario_id)
                if usuario_existente:
                    propietario_resuelto = str(usuario_existente["id"])
            except ValueError:
                propietario_id = ""

        if not propietario_resuelto and propietario_email:
            usuario_por_email = Usuario_controller.obtener_usuario_por_email((propietario_email or "").strip().lower())
            if usuario_por_email:
                propietario_resuelto = str(usuario_por_email["id"])

        if inversionista_id:
            try:
                UUID(inversionista_id)
                usuario_inversionista = Usuario_controller.obtener_datos_usuario(inversionista_id)
                if usuario_inversionista:
                    inversionista_resuelto = str(usuario_inversionista["id"])
            except ValueError:
                inversionista_id = ""

        proyectos = Proyecto_controller.listar_proyectos(
            propietario_id=propietario_resuelto,
            inversionista_id=inversionista_resuelto,
        )
        return {"ok": True, "proyectos": proyectos}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.get("/api/v1/analytics/proyectos")
def analytics_proyectos(propietario_id: str | None = None):
    """Devuelve métricas y series para los proyectos de un propietario (emprendedor)."""
    try:
        if not propietario_id:
            return {"ok": False, "mensaje": "Parámetro 'propietario_id' requerido"}

        # Validar usuario
        try:
            UUID(propietario_id)
            usuario = Usuario_controller.obtener_datos_usuario(propietario_id)
            if not usuario:
                return {"ok": False, "mensaje": "Propietario no encontrado"}
        except Exception:
            return {"ok": False, "mensaje": "propietario_id inválido"}

        datos = Proyecto_controller.obtener_analiticas_propietario(propietario_id)
        return {"ok": True, "analiticas": datos}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error interno del servidor: {str(e)}"}


@app.get("/api/v1/analytics/proyeccion")
def analytics_proyeccion(proyecto_id: str | None = None, meses_historial: int | None = 6, meses_prediccion: int | None = 3, include_mensajes: bool | None = False):
    """Devuelve proyección para un proyecto usando historial de solicitudes e inversiones."""
    try:
        if not proyecto_id:
            return {"ok": False, "mensaje": "Parámetro 'proyecto_id' requerido"}

        try:
            UUID(proyecto_id)
        except Exception:
            return {"ok": False, "mensaje": "proyecto_id inválido"}

        datos = Proyecto_controller.obtener_proyeccion_proyecto(
            proyecto_id,
            meses_historial=meses_historial or 6,
            meses_prediccion=meses_prediccion or 3,
            include_mensajes=bool(include_mensajes)
        )
        return {"ok": True, "proyeccion": datos}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error interno del servidor: {str(e)}"}


@app.post("/api/v1/proyectos")
def crear_proyecto(payload: ProyectoRequest, background_tasks: BackgroundTasks):
    titulo = (payload.titulo or "").strip()
    estado = (payload.estado or "activo").strip().lower()
    presupuesto = payload.presupuesto or 0

    def _resolver_propietario_id():
        propietario_id = (payload.propietario_id or "").strip()
        if propietario_id:
            try:
                UUID(propietario_id)
            except ValueError:
                propietario_id = ""

        if propietario_id:
            usuario_existente = Usuario_controller.obtener_datos_usuario(propietario_id)
            if usuario_existente:
                return str(usuario_existente["id"])

        propietario_email = (payload.propietario_email or "").strip().lower()
        if propietario_email:
            usuario_por_email = Usuario_controller.obtener_usuario_por_email(propietario_email)
            if usuario_por_email:
                return str(usuario_por_email["id"])

        return None

    if presupuesto < 0:
        return {"ok": False, "mensaje": "El presupuesto no puede ser negativo"}

    if presupuesto > 999999999999.99:
        return {"ok": False, "mensaje": "El presupuesto máximo permitido es 999,999,999,999.99"}

    if estado not in {"activo", "inactivo"}:
        return {"ok": False, "mensaje": "Estado inválido. Usa activo o inactivo"}

    try:
        propietario_resuelto = _resolver_propietario_id()

        if not propietario_resuelto or not titulo:
            return {"ok": False, "mensaje": "No se pudo resolver el propietario del proyecto"}

        proyecto = Proyecto_controller.insertar_proyecto(
            propietario_id=propietario_resuelto,
            titulo=titulo,
            descripcion=payload.descripcion or "",
            presupuesto=presupuesto,
            estado=estado,
            fecha_publicacion=payload.fecha_publicacion or datetime.now(timezone.utc).isoformat(),
        )

        try:
            crear_notificacion_usuario(
                usuario_id=propietario_resuelto,
                tipo="proyecto",
                titulo="Proyecto creado",
                mensaje=f"Tu proyecto '{titulo}' fue creado correctamente.",
                ruta_destino="proyectos",
                metadata={"proyecto_id": proyecto["id"] if isinstance(proyecto, dict) else None},
            )
        except Exception:
            pass

        # Disparar análisis automático en segundo plano
        if isinstance(proyecto, dict) and proyecto.get("id"):
            background_tasks.add_task(generar_score_automatico, proyecto["id"])

        return {"ok": True, "mensaje": "Proyecto creado", "proyecto": proyecto}
    except Exception as error:
        return {"ok": False, "mensaje": str(error) or "No se pudo crear el proyecto"}


@app.patch("/api/v1/proyectos/{proyecto_id}")
def actualizar_proyecto(proyecto_id: str, payload: ProyectoRequest, background_tasks: BackgroundTasks):
    try:
        print(f"[Proyectos] Actualizando proyecto: {proyecto_id}")
        
        # Verificar si el proyecto existe
        proyecto_actual = Proyecto_controller.obtener_proyecto(proyecto_id)
        if not proyecto_actual:
            return {"ok": False, "mensaje": "Proyecto no encontrado"}

        # Actualizar en la base de datos
        exito = Proyecto_controller.actualizar_proyecto(
            proyecto_id=proyecto_id,
            titulo=payload.titulo,
            descripcion=payload.descripcion,
            presupuesto=payload.presupuesto,
            estado=payload.estado
        )

        if exito:
            # Si cambió el título o descripción, disparar nuevo análisis IA
            if (payload.titulo and payload.titulo != proyecto_actual["titulo"]) or \
               (payload.descripcion and payload.descripcion != proyecto_actual["descripcion"]):
                print(f"[Proyectos] Disparando re-scoring por cambios en contenido")
                # Limpiar el análisis viejo antes de disparar el nuevo
                Proyecto_controller.actualizar_analisis_ai(proyecto_id, None)
                background_tasks.add_task(generar_score_automatico, proyecto_id)

            return {"ok": True, "mensaje": "Proyecto actualizado correctamente"}
        else:
            return {"ok": False, "mensaje": "No se pudo actualizar el proyecto"}
            
    except Exception as error:
        print(f"[Proyectos] Error al actualizar: {str(error)}")
        return {"ok": False, "mensaje": str(error)}


@app.get("/api/v1/proyectos/{proyecto_id}")
def obtener_proyecto(proyecto_id: str):
    try:
        print(f"[Proyectos] Obteniendo detalles de proyecto: {proyecto_id}")
        proyecto = Proyecto_controller.obtener_proyecto(proyecto_id)
        if not proyecto:
            return {"ok": False, "mensaje": "Proyecto no encontrado"}
        return {"ok": True, "proyecto": proyecto}
    except Exception as error:
        print(f"[Proyectos] Error al obtener detalles de proyecto: {str(error)}")
        return {"ok": False, "mensaje": f"Error interno del servidor: {str(error)}"}


@app.get("/api/v1/notificaciones")
def listar_notificaciones(usuario_id: str | None = None):
    try:
        notificaciones = listar_notificaciones_usuario(usuario_id or "")
        return {"ok": True, "notificaciones": notificaciones}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.post("/api/v1/notificaciones")
def crear_notificacion(payload: CrearNotificacionRequest):
    try:
        if (payload.tipo or "").strip() == "mensaje":
            print(f"[Notificación] Se omitió el guardado en Firestore para una notificación de mensaje del usuario: {payload.usuario_id}")
            return {"ok": True, "mensaje": "Notificación de mensaje omitida"}

        print(f"[Notificación] Creando notificación para usuario: {payload.usuario_id}")
        notification_id = crear_notificacion_usuario(
            usuario_id=payload.usuario_id,
            tipo=payload.tipo,
            titulo=payload.titulo,
            mensaje=payload.mensaje or "",
            ruta_destino=payload.ruta_destino,
            metadata=payload.metadata or {},
        )
        
        if not notification_id:
            print(f"[Notificación] Error: No se retornó un ID válido")
            return {"ok": False, "mensaje": "No se pudo crear la notificación"}
        
        print(f"[Notificación] Notificación creada exitosamente con ID: {notification_id}")
        return {"ok": True, "mensaje": "Notificación creada", "notification_id": notification_id}
    except Exception as error:
        print(f"[Notificación] Excepción al crear notificación: {str(error)}")
        return {"ok": False, "mensaje": f"Error al crear notificación: {str(error)}"}


@app.patch("/api/v1/notificaciones/{notification_id}/leida")
def marcar_notificacion_como_leida(notification_id: str):
    try:
        if not marcar_notificacion_leida(notification_id):
            return {"ok": False, "mensaje": "No se pudo marcar como leída"}
        return {"ok": True, "mensaje": "Notificación marcada como leída"}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.patch("/api/v1/notificaciones/leidas")
def marcar_todas_leidas(payload: NotificacionesRequest):
    try:
        actualizadas = marcar_todas_notificaciones_leidas(payload.usuario_id)
        return {"ok": True, "actualizadas": actualizadas}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.delete("/api/v1/notificaciones/{notification_id}")
def borrar_notificacion(notification_id: str):
    try:
        if not eliminar_notificacion(notification_id):
            return {"ok": False, "mensaje": "No se pudo eliminar la notificación"}
        return {"ok": True, "mensaje": "Notificación eliminada"}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


# ============= PRUEBA PATCH =============

@app.patch("/api/v1/test-patch")
def test_patch():
    print("[TEST] PATCH request recibido en /api/v1/test-patch")
    return {"ok": True, "mensaje": "PATCH funciona correctamente"}


# ============= SOLICITUDES DE INVERSIÓN =============

@app.post("/api/v1/solicitudes")
def crear_solicitud(payload: SolicitudInversionCreate, background_tasks: BackgroundTasks):
    try:
        print(f"[Solicitud] Creando solicitud para proyecto: {payload.proyecto_id}")
        resultado = crear_solicitud_inversion(
            proyecto_id=payload.proyecto_id,
            inversionista_id=payload.inversionista_id,
            monto_solicitado=payload.monto_solicitado,
            propuesta=payload.propuesta,
        )
        
        if not resultado:
            print(f"[Solicitud] Error: No se retornó un resultado válido")
            return CrearSolicitudResponse(ok=False, mensaje="No se pudo crear la solicitud")
        
        # Programar envío de correo al propietario del proyecto
        try:
            proyecto = Proyecto_controller.obtener_proyecto(payload.proyecto_id)
            if proyecto and proyecto.get("propietario_id"):
                propietario = Usuario_controller.obtener_datos_usuario(proyecto.get("propietario_id"))
                if propietario and propietario.get("email"):
                    correo_prop = propietario.get("email")
                    nombre_prop = propietario.get("nombre")
                    monto = float(payload.monto_solicitado or 0)
                    inversionista_nombre = "Inversionista"
                    try:
                        usuario_inversionista = Usuario_controller.obtener_datos_usuario(payload.inversionista_id)
                        if usuario_inversionista and usuario_inversionista.get("nombre"):
                            inversionista_nombre = usuario_inversionista.get("nombre")
                    except Exception as e:
                        print(f"[Solicitud] No se pudo resolver el nombre del inversionista: {e}")

                    print(f"[Solicitud] Enviando email de nueva solicitud a {correo_prop} para proyecto {proyecto.get('titulo')}")
                    resultado_email = sendgrid_service.send_investment_request_email(
                        correo_prop,
                        nombre_prop,
                        proyecto.get("titulo"),
                        monto,
                        inversionista_nombre,
                        resultado.get("id"),
                        None,
                    )
                    print(f"[Solicitud] Resultado email nueva solicitud: {resultado_email}")
        except Exception as e:
            print(f"[Solicitud] No se pudo enviar email de nueva solicitud: {e}")

        print(f"[Solicitud] Solicitud creada exitosamente con ID: {resultado.get('id')}")
        return CrearSolicitudResponse(ok=True, solicitud_id=resultado.get('id'))
    except Exception as error:
        print(f"[Solicitud] Excepción al crear solicitud: {str(error)}")
        return CrearSolicitudResponse(ok=False, mensaje=f"Error al crear solicitud: {str(error)}")


@app.get("/api/v1/solicitudes/proyecto/{proyecto_id}")
def listar_solicitudes_proyecto(proyecto_id: str):
    try:
        print(f"[Solicitud] Listando solicitudes para proyecto: {proyecto_id}")
        solicitudes = listar_solicitudes_por_proyecto(proyecto_id)
        print(f"[Solicitud] Total de solicitudes: {len(solicitudes)}")
        return ListarSolicitudesResponse(ok=True, solicitudes=solicitudes)
    except Exception as error:
        print(f"[Solicitud] Error al listar solicitudes del proyecto: {str(error)}")
        return ListarSolicitudesResponse(ok=False, mensaje=f"Error: {str(error)}")


@app.get("/api/v1/solicitudes/inversionista/{inversionista_id}")
def listar_solicitudes_inversionista(inversionista_id: str):
    try:
        print(f"[Solicitud] Listando solicitudes del inversionista: {inversionista_id}")
        solicitudes = listar_solicitudes_por_inversionista(inversionista_id)
        print(f"[Solicitud] Total de solicitudes: {len(solicitudes)}")
        return ListarSolicitudesResponse(ok=True, solicitudes=solicitudes)
    except Exception as error:
        print(f"[Solicitud] Error al listar solicitudes del inversionista: {str(error)}")
        return ListarSolicitudesResponse(ok=False, mensaje=f"Error: {str(error)}")


@app.get("/api/v1/solicitudes/{solicitud_id}")
def obtener_solicitud_detalles(solicitud_id: str):
    try:
        print(f"[Solicitud] Obteniendo detalles de solicitud: {solicitud_id}")
        solicitud = obtener_solicitud(solicitud_id)
        
        if not solicitud:
            return {"ok": False, "mensaje": "Solicitud no encontrada"}
        
        return {"ok": True, "solicitud": solicitud}
    except Exception as error:
        print(f"[Solicitud] Error al obtener solicitud: {str(error)}")
        return {"ok": False, "mensaje": f"Error: {str(error)}"}


@app.patch("/api/v1/solicitudes/{solicitud_id}")
def actualizar_solicitud(solicitud_id: str, payload: SolicitudInversionUpdate, background_tasks: BackgroundTasks):
    try:
        print(f"[Solicitud] Actualizando solicitud: {solicitud_id}, nuevo estado: {payload.estado}")
        
        if not payload.estado:
            print(f"[Solicitud] Error: No se especificó estado")
            return ActualizarSolicitudResponse(ok=False, mensaje="Estado requerido")
        
        resultado = actualizar_estado_solicitud(solicitud_id, payload.estado)
        
        print(f"[Solicitud] Resultado de actualizar_estado_solicitud: {resultado}")
        
        if resultado:
            print(f"[Solicitud] Solicitud actualizada exitosamente a estado: {payload.estado}")

            # Si la solicitud fue aceptada o rechazada, enviar un email al inversionista
            try:
                nuevo_estado = (payload.estado or "").lower()
                if nuevo_estado in ("aceptada", "rechazada"):
                    inversionista_usuario_id = resultado.get("inversionista_usuario_id")
                    proyecto_titulo = resultado.get("proyecto_titulo") or "Tu proyecto"
                    monto = resultado.get("monto_solicitado") or 0
                    if inversionista_usuario_id:
                        try:
                            usuario_inversionista = Usuario_controller.obtener_datos_usuario(str(inversionista_usuario_id))
                            if usuario_inversionista and usuario_inversionista.get("email"):
                                correo = usuario_inversionista.get("email")
                                nombre = usuario_inversionista.get("nombre")
                                print(f"[Solicitud] Enviando email de respuesta a {correo} para solicitud {solicitud_id}")
                                resultado_email = sendgrid_service.send_investment_response_email(
                                    correo,
                                    nombre,
                                    proyecto_titulo,
                                    float(monto or 0),
                                    nuevo_estado,
                                    solicitud_id,
                                    None,
                                )
                                print(f"[Solicitud] Resultado email respuesta solicitud: {resultado_email}")
                            else:
                                print(f"[Solicitud] Inversionista {inversionista_usuario_id} sin email; no se envía correo")
                        except Exception as e:
                            print(f"[Solicitud] Error al enviar email al inversionista: {e}")
            except Exception:
                pass

            return ActualizarSolicitudResponse(ok=True, mensaje="Solicitud actualizada")
        else:
            print(f"[Solicitud] Error: actualizar_estado_solicitud retornó None")
            return ActualizarSolicitudResponse(ok=False, mensaje="No se pudo actualizar la solicitud - sin resultado")
    except Exception as error:
        print(f"[Solicitud] Excepción al actualizar solicitud: {str(error)}")
        import traceback
        traceback.print_exc()
        return ActualizarSolicitudResponse(ok=False, mensaje=f"Error: {str(error)}")


@app.delete("/api/v1/solicitudes/{solicitud_id}")
def borrar_solicitud(solicitud_id: str):
    try:
        print(f"[Solicitud] Eliminando solicitud: {solicitud_id}")
        
        if eliminar_solicitud(solicitud_id):
            print(f"[Solicitud] Solicitud eliminada exitosamente")
            return {"ok": True, "mensaje": "Solicitud eliminada"}
        
        return {"ok": False, "mensaje": "No se pudo eliminar la solicitud"}
    except Exception as error:
        print(f"[Solicitud] Error al eliminar solicitud: {str(error)}")
        return {"ok": False, "mensaje": f"Error: {str(error)}"}


@app.post("/api/v1/auth/login")
def login_usuario(payload: LoginRequest, background_tasks: BackgroundTasks):
    email = payload.email.strip()
    password = payload.password or ""
    tipo_usuario = (payload.tipo_usuario or "").strip()

    if not email or not password:
        return {"ok": False, "mensaje": "Email y password son obligatorios"}

    try:
        resultado_login = Usuario.login(email=email, password=password)
        usuario = resultado_login.get("usuario") or {}
        rol_usuario = str(usuario.get("rol") or "").strip().lower()

        if not usuario.get("activo", True):
            if usuario.get("pendiente_aprobacion"):
                return {
                    "ok": False,
                    "mensaje": "Tu cuenta está pendiente de aprobación. Te avisaremos por correo cuando sea confirmada.",
                }
            return {"ok": False, "mensaje": "Tu cuenta está bloqueada. Contacta al administrador"}

        if tipo_usuario and tipo_usuario not in {"emprendedor", "inversionista", "admin"}:
            return {"ok": False, "mensaje": "Rol de usuario no válido"}

        if tipo_usuario and rol_usuario and rol_usuario != tipo_usuario and rol_usuario != "admin":
            return {"ok": False, "mensaje": "El rol seleccionado no coincide con tu cuenta"}

        # Programar notificación de inicio de sesión
        try:
            usuario_email = usuario.get("email")
            usuario_nombre = usuario.get("nombre") or usuario.get("nombre_usuario")
            if usuario_email:
                background_tasks.add_task(sendgrid_service.send_login_alert, usuario_email, usuario_nombre)
        except Exception:
            pass

        return {
            "ok": True,
            "mensaje": "Inicio de sesión exitoso",
            "token": resultado_login.get("id_token"),
            "refresh_token": resultado_login.get("refresh_token"),
            "usuario": usuario,
            "es_admin": rol_usuario == "admin",
        }
    except ValueError as error_login:
        return {"ok": False, "mensaje": str(error_login)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.post("/api/v1/register")
def registrar_usuario(payload: RegistroRequest, background_tasks: BackgroundTasks):
    email = payload.email.strip().lower()
    password = payload.password or ""
    confirm_password = payload.confirm_password or ""
    tipo_usuario = (payload.tipo_usuario or "").strip().lower()
    nombre_usuario = (payload.nombre_usuario or "").strip()
    nombre = (payload.nombre or nombre_usuario or "").strip()

    if not email or not password or not confirm_password or not nombre_usuario:
        return {"ok": False, "mensaje": "Nombre de usuario, email y contraseña son obligatorios"}

    if password != confirm_password:
        return {"ok": False, "mensaje": "Las contraseñas no coinciden"}

    if not payload.acepta_terminos:
        return {"ok": False, "mensaje": "Debes aceptar los términos y condiciones"}

    if tipo_usuario == "admin":
        return {"ok": False, "mensaje": "Solo otro administrador puede crear una cuenta admin"}

    if tipo_usuario not in {"emprendedor", "inversionista"}:
        return {"ok": False, "mensaje": "Rol de usuario no válido"}

    registro_libre = Usuario_controller.obtener_estado_registro_libre()
    requiere_aprobacion = not registro_libre

    firebase_uid = None

    try:
        nuevo_usuario_firebase = admin_auth.create_user(
            email=email,
            password=password,
            display_name=nombre,
        )
        firebase_uid = nuevo_usuario_firebase.uid

        registro = Usuario_controller.registrar_usuario_completo(
            rol=tipo_usuario,
            nombre=nombre,
            email=email,
            nombre_usuario=nombre_usuario,
            firebase_uid=firebase_uid,
            activo=not requiere_aprobacion,
            pendiente_aprobacion=requiere_aprobacion,
            telefono=payload.telefono,
            website=payload.website,
            linkedin=payload.linkedin,
            ciudad=payload.ciudad,
            descripcion=payload.descripcion,
            biografia=payload.biografia,
            licencias_certificaciones=payload.licencias_certificaciones or [],
            intereses_inversion=payload.intereses_inversion or [],
            monto_disponible=payload.monto_disponible or 0,
        )

        if not requiere_aprobacion:
            # Enviar correo de bienvenida en segundo plano si el registro es libre
            try:
                correo = registro["usuario"].get("email")
                nombre_usuario_reg = registro["usuario"].get("nombre") or registro["usuario"].get("nombre_usuario")
                if correo:
                    background_tasks.add_task(sendgrid_service.send_welcome_email, correo, nombre_usuario_reg)
            except Exception:
                pass

        return {
            "ok": True,
            "mensaje": "Registro exitoso" if not requiere_aprobacion else "Registro recibido. Tu cuenta está pendiente de aprobación.",
            "requiere_aprobacion": requiere_aprobacion,
            "usuario": registro["usuario"],
            "perfil": registro["perfil"],
        }
    except ValueError as error_registro:
        if firebase_uid:
            try:
                admin_auth.delete_user(firebase_uid)
            except Exception:
                pass
        return {"ok": False, "mensaje": str(error_registro)}
    except Exception as error_registro:
        if firebase_uid:
            try:
                admin_auth.delete_user(firebase_uid)
            except Exception:
                pass
        return {"ok": False, "mensaje": str(error_registro) or "No se pudo registrar el usuario"}


@app.get("/api/v1/admin/usuarios")
def admin_listar_usuarios(request: Request, excluir_usuario_id: str | None = None):
    try:
        administrador = _obtener_usuario_autenticado(request, requiere_admin=True)
        usuarios = Usuario_controller.listar_usuarios(excluir_usuario_id=excluir_usuario_id)
        return {
            "ok": True,
            "usuarios": usuarios,
            "administrador": {
                "id": administrador.get("id"),
                "email": administrador.get("email"),
                "rol": administrador.get("rol"),
            },
        }
    except ValueError as error_admin:
        return {"ok": False, "mensaje": str(error_admin)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.post("/api/v1/admin/usuarios/admin")
def admin_crear_admin(payload: AdminRegistroRequest, request: Request):
    email = payload.email.strip().lower()
    password = payload.password or ""
    confirm_password = payload.confirm_password or ""
    nombre_usuario = (payload.nombre_usuario or "").strip()
    nombre = (payload.nombre or nombre_usuario or "").strip()

    if not nombre_usuario or not email or not password or not confirm_password:
        return {"ok": False, "mensaje": "Nombre de usuario, email y contraseña son obligatorios"}

    if password != confirm_password:
        return {"ok": False, "mensaje": "Las contraseñas no coinciden"}

    if not payload.acepta_terminos:
        return {"ok": False, "mensaje": "Debes aceptar los términos y condiciones"}

    firebase_uid = None

    try:
        administrador = _obtener_usuario_autenticado(request, requiere_admin=True)

        nuevo_usuario_firebase = admin_auth.create_user(
            email=email,
            password=password,
            display_name=nombre or nombre_usuario,
        )
        firebase_uid = nuevo_usuario_firebase.uid

        registro = Usuario_controller.registrar_usuario_completo(
            rol="admin",
            nombre=nombre,
            email=email,
            nombre_usuario=nombre_usuario,
            firebase_uid=firebase_uid,
            telefono=payload.telefono,
            website=payload.website,
            linkedin=payload.linkedin,
            ciudad=payload.ciudad,
            descripcion=payload.descripcion,
            biografia=payload.biografia,
            permitir_admin=True,
        )

        return {
            "ok": True,
            "mensaje": "Administrador creado exitosamente",
            "creado_por": {
                "id": administrador.get("id"),
                "email": administrador.get("email"),
            },
            "usuario": registro["usuario"],
            "perfil": registro["perfil"],
        }
    except ValueError as error_admin:
        if firebase_uid:
            try:
                admin_auth.delete_user(firebase_uid)
            except Exception:
                pass
        return {"ok": False, "mensaje": str(error_admin)}
    except Exception as error_admin:
        if firebase_uid:
            try:
                admin_auth.delete_user(firebase_uid)
            except Exception:
                pass
        return {"ok": False, "mensaje": str(error_admin) or "No se pudo crear el administrador"}
@app.patch("/api/v1/admin/usuarios/{usuario_id}/estado")
def admin_actualizar_estado_usuario(usuario_id: str, payload: EstadoUsuarioRequest, request: Request, background_tasks: BackgroundTasks):
    try:
        administrador = _obtener_usuario_autenticado(request, requiere_admin=True)
        usuario_objetivo = Usuario_controller.obtener_datos_usuario(usuario_id)

        if not usuario_objetivo:
            return {"ok": False, "mensaje": "Usuario no encontrado"}

        if str(usuario_objetivo.get("id")) == str(administrador.get("id")) and not payload.activo:
            return {"ok": False, "mensaje": "No puedes desactivar tu propia cuenta desde este panel"}

        if str(usuario_objetivo.get("rol") or "").lower() == "admin" and not payload.activo:
            admins_restantes = Usuario_controller.contar_admins_activos(excluir_usuario_id=usuario_id)
            if admins_restantes <= 0:
                return {"ok": False, "mensaje": "No puedes desactivar el último administrador activo"}

        usuario_actualizado = Usuario_controller.actualizar_estado_usuario(usuario_id, payload.activo, pendiente_aprobacion=False)
        if not usuario_actualizado:
            return {"ok": False, "mensaje": "No se pudo actualizar el estado del usuario"}

        if payload.activo and usuario_objetivo.get("pendiente_aprobacion"):
            try:
                correo = usuario_objetivo.get("email")
                nombre_usuario_objetivo = usuario_objetivo.get("nombre") or usuario_objetivo.get("nombre_usuario")
                if correo:
                    background_tasks.add_task(
                        sendgrid_service.send_registration_approved_email,
                        correo,
                        nombre_usuario_objetivo,
                    )
            except Exception:
                pass

        return {
            "ok": True,
            "mensaje": (
                "Usuario aprobado correctamente"
                if payload.activo and usuario_objetivo.get("pendiente_aprobacion")
                else f"Usuario {'activado' if payload.activo else 'bloqueado'} correctamente"
            ),
            "usuario": {
                "id": usuario_actualizado[0],
                "firebase_uid": usuario_actualizado[1],
                "nombre": usuario_actualizado[2],
                "email": usuario_actualizado[3],
                "rol": usuario_actualizado[4],
                "activo": usuario_actualizado[5],
                "pendiente_aprobacion": usuario_actualizado[6],
            },
        }
    except ValueError as error_admin:
        return {"ok": False, "mensaje": str(error_admin)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.delete("/api/v1/admin/usuarios/{usuario_id}/rechazar-registro")
def admin_rechazar_registro_usuario(usuario_id: str, request: Request):
    try:
        administrador = _obtener_usuario_autenticado(request, requiere_admin=True)
        usuario_objetivo = Usuario_controller.obtener_datos_usuario(usuario_id)

        if not usuario_objetivo:
            return {"ok": False, "mensaje": "Usuario no encontrado"}

        if not usuario_objetivo.get("pendiente_aprobacion"):
            return {"ok": False, "mensaje": "Solo puedes rechazar usuarios pendientes de aprobación"}

        usuario_eliminado = Usuario_controller.eliminar_usuario_pendiente(usuario_id)
        if not usuario_eliminado:
            return {"ok": False, "mensaje": "No se pudo rechazar el registro"}

        firebase_uid = usuario_eliminado[1]
        if firebase_uid:
            try:
                admin_auth.delete_user(firebase_uid)
            except Exception:
                pass

        return {
            "ok": True,
            "mensaje": "Registro rechazado correctamente",
            "rechazado_por": {
                "id": administrador.get("id"),
                "email": administrador.get("email"),
            },
            "usuario": {
                "id": usuario_eliminado[0],
                "firebase_uid": usuario_eliminado[1],
                "nombre": usuario_eliminado[2],
                "email": usuario_eliminado[3],
                "rol": usuario_eliminado[4],
                "activo": usuario_eliminado[5],
                "pendiente_aprobacion": usuario_eliminado[6],
            },
        }
    except ValueError as error_admin:
        return {"ok": False, "mensaje": str(error_admin)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.post("/api/v1/admin/bootstrap")
def bootstrap_primer_admin(payload: BootstrapAdminRequest):
    bootstrap_secret = _obtener_bootstrap_secret()

    if not bootstrap_secret:
        return {"ok": False, "mensaje": "Bootstrap de admin no configurado en el servidor"}

    if payload.bootstrap_secret.strip() != bootstrap_secret:
        return {"ok": False, "mensaje": "Secreto de bootstrap inválido"}

    if Usuario_controller.contar_admins_totales() > 0:
        return {"ok": False, "mensaje": "Ya existe al menos un administrador; usa el panel admin"}

    email = payload.email.strip().lower()
    password = payload.password or ""
    confirm_password = payload.confirm_password or ""
    nombre_usuario = (payload.nombre_usuario or "").strip()
    nombre = (payload.nombre or nombre_usuario or "").strip()

    if not nombre_usuario or not email or not password or not confirm_password:
        return {"ok": False, "mensaje": "Nombre de usuario, email y contraseña son obligatorios"}

    if password != confirm_password:
        return {"ok": False, "mensaje": "Las contraseñas no coinciden"}

    if not payload.acepta_terminos:
        return {"ok": False, "mensaje": "Debes aceptar los términos y condiciones"}

    firebase_uid = None

    try:
        nuevo_usuario_firebase = admin_auth.create_user(
            email=email,
            password=password,
            display_name=nombre or nombre_usuario,
        )
        firebase_uid = nuevo_usuario_firebase.uid

        registro = Usuario_controller.registrar_usuario_completo(
            rol="admin",
            nombre=nombre,
            email=email,
            nombre_usuario=nombre_usuario,
            firebase_uid=firebase_uid,
            activo=True,
            pendiente_aprobacion=False,
            telefono=payload.telefono,
            website=payload.website,
            linkedin=payload.linkedin,
            ciudad=payload.ciudad,
            descripcion=payload.descripcion,
            biografia=payload.biografia,
            permitir_admin=True,
        )

        return {
            "ok": True,
            "mensaje": "Administrador inicial creado exitosamente",
            "usuario": registro["usuario"],
            "perfil": registro["perfil"],
        }
    except ValueError as error_admin:
        return {"ok": False, "mensaje": str(error_admin)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


# ================== ADMIN TICKET MANAGEMENT ==================

@app.get("/api/v1/admin/tickets")
def admin_listar_tickets(request: Request,
                         categoria: str | None = Query(None),
                         prioridad: str | None = Query(None),
                         estado: str | None = Query(None),
                         asignado_a: str | None = Query(None)):
    """List and filter tickets for admin users."""
    try:
        _obtener_usuario_autenticado(request, requiere_admin=True)
        filtro: dict = {}
        if categoria:
            filtro["categoria"] = categoria
        if prioridad:
            filtro["prioridad"] = prioridad
        if estado:
            filtro["estado"] = estado
        if asignado_a:
            filtro["asignado_a"] = asignado_a
        tickets = listar_tickets(filtro if filtro else None)
        sincronizar_tickets_firestore(tickets)
        return {"ok": True, "tickets": tickets}
    except ValueError as error_admin:
        return {"ok": False, "mensaje": str(error_admin)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}

@app.get("/api/v1/admin/tickets/{ticket_id}")
def admin_obtener_ticket(ticket_id: str, request: Request):
    """Get a specific ticket by ID for admin users."""
    try:
        _obtener_usuario_autenticado(request, requiere_admin=True)
        ticket = obtener_ticket(ticket_id)
        if not ticket:
            return {"ok": False, "mensaje": "Ticket no encontrado"}
        return {"ok": True, "ticket": ticket}
    except ValueError as error_admin:
        return {"ok": False, "mensaje": str(error_admin)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}

@app.patch("/api/v1/admin/tickets/{ticket_id}")
def admin_actualizar_ticket(ticket_id: str, payload: TicketUpdate, request: Request):
    """Update priority, status, assign agent, and internal notes for a ticket."""
    try:
        _obtener_usuario_autenticado(request, requiere_admin=True)
        ticket = actualizar_ticket(ticket_id, payload)
        if not ticket:
            return {"ok": False, "mensaje": "Ticket no encontrado"}
        sincronizar_ticket_firestore(ticket)
        return {"ok": True, "ticket": ticket}
    except ValueError as error_admin:
        return {"ok": False, "mensaje": str(error_admin)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}

# Cleanup leftover bootstrap error handling (removed)


# ================== USER TICKET ENDPOINTS ==================

@app.post("/api/v1/tickets")
def api_crear_ticket(payload: TicketCreate, request: Request):
    """Permite a cualquier usuario autenticado crear un ticket de soporte."""
    try:
        usuario = _obtener_usuario_autenticado(request)
        ticket = crear_ticket(payload, usuario_id=usuario.get("id"))
        sincronizar_ticket_firestore(ticket)
        return {"ok": True, "ticket": ticket}
    except ValueError as error_user:
        return {"ok": False, "mensaje": str(error_user)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.get("/api/v1/tickets")
def api_listar_tickets(request: Request):
    """Permite a cualquier usuario autenticado ver sus propios tickets."""
    try:
        usuario = _obtener_usuario_autenticado(request)
        # Filtrar por el ID del usuario para que solo vea los suyos
        tickets = listar_tickets({"usuario_id": usuario.get("id")})
        return {"ok": True, "tickets": tickets}
    except ValueError as error_user:
        return {"ok": False, "mensaje": str(error_user)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}



@app.get("/api/v1/admin/config/registro-libre")
def admin_obtener_config_registro_libre(request: Request):
    try:
        _obtener_usuario_autenticado(request, requiere_admin=True)
        valor = Usuario_controller.obtener_estado_registro_libre()
        return {"ok": True, "registro_libre": valor}
    except ValueError as error_admin:
        return {"ok": False, "mensaje": str(error_admin)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.patch("/api/v1/admin/config/registro-libre")
def admin_actualizar_config_registro_libre(payload: EstadoRegistroRequest, request: Request):
    try:
        _obtener_usuario_autenticado(request, requiere_admin=True)
        valor = Usuario_controller.actualizar_estado_registro_libre(payload.registro_libre)
        return {
            "ok": True,
            "mensaje": "Registro libre actualizado",
            "registro_libre": valor,
        }
    except ValueError as error_admin:
        return {"ok": False, "mensaje": str(error_admin)}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.get("/api/v1/usuarios/{usuario_id}")
def obtener_usuario(usuario_id: str):
    try:
        usuario = Usuario_controller.obtener_datos_usuario(usuario_id)

        if usuario is None:
            return {"ok": False, "mensaje": "Usuario no encontrado"}

        return {"ok": True, "usuario": usuario}
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.patch("/api/v1/usuarios/{usuario_id}")
def actualizar_usuario(usuario_id: str, payload: PerfilUsuarioRequest):
    try:
        usuario = Usuario_controller.actualizar_datos_usuario(
            usuario_id=usuario_id,
            telefono=payload.telefono,
            website=payload.website,
            linkedin=payload.linkedin,
            ciudad=payload.ciudad,
            descripcion=payload.descripcion,
        )

        if usuario is None:
            return {"ok": False, "mensaje": "Usuario no encontrado"}

        return {
            "ok": True,
            "mensaje": "Perfil actualizado",
            "usuario": {
                "id": usuario[0],
                "telefono": usuario[1],
                "website": usuario[2],
                "linkedin": usuario[3],
                "ciudad": usuario[4],
                "descripcion": usuario[5],
            },
        }
    except Exception:
        return {"ok": False, "mensaje": "Error interno del servidor"}


@app.post("/api/v1/usuarios/{usuario_id}/foto")
async def subir_foto_perfil(usuario_id: str, file: UploadFile = File(...)):
    try:
        # Guardar archivo temporalmente para subirlo a Cloudinary
        # O podemos pasar el file object directamente si Cloudinary lo soporta
        # subir_imagen acepta file_path o stream
        
        # Leemos el contenido del archivo
        file_content = await file.read()
        
        # Subimos a Cloudinary
        url_foto = subir_imagen(file_content, folder=f"olympo/users/{usuario_id}")
        
        if not url_foto:
            return {"ok": False, "mensaje": "Error al subir imagen a Cloudinary"}
            
        # Actualizamos en la base de datos
        Usuario_controller.actualizar_foto_perfil(usuario_id, url_foto)
        
        return {"ok": True, "mensaje": "Foto de perfil actualizada", "url": url_foto}
    except Exception as e:
        print(f"Error en subir_foto_perfil: {e}")
        return {"ok": False, "mensaje": f"Error: {str(e)}"}


@app.post("/api/v1/chatbot/mensaje")
def mensaje_chatbot(payload: ChatbotRequest):
    mensaje_usuario = (payload.mensaje or "").strip()

    if not mensaje_usuario:
        return {"ok": False, "mensaje": "El mensaje no puede estar vacío"}

    try:
        respuesta_bot = IAAsistente.mensaje_chatbot(mensaje_usuario, usuario_id=payload.usuario_id)
        # Guardar intercambio en Firestore para mantener historial
        try:
            timestamp = datetime.now(timezone.utc)
            hist_ref = firestore_db.collection("chatbot_history_v2").document()
            hist_ref.set(
                {
                    "userId": payload.usuario_id,
                    "userMessage": mensaje_usuario,
                    "botResponse": respuesta_bot,
                    "createdAt": timestamp,
                }
            )
        except Exception:
            # No romper la respuesta del chatbot si falla el guardado
            pass

        return {"ok": True, "respuesta": respuesta_bot}
    except ValueError as error:
        return {"ok": False, "mensaje": str(error)}
    except Exception as error:
        return {"ok": False, "mensaje": f"Error en chatbot: {str(error)}"}


@app.get("/api/v1/chatbot/history")
def historial_chatbot(usuario_id: str, limit: int | None = 200):
    try:
        print(f"[Chatbot] Buscando historial para el usuario: '{usuario_id}'")
        lim = int(limit) if limit else 200
        
        # Filtro estricto por userId
        coleccion_ref = firestore_db.collection("chatbot_history_v2")
        query = coleccion_ref.where("userId", "==", usuario_id).limit(lim)
        docs = query.stream()

        resultados = []
        for doc in docs:
            data = doc.to_dict()
            
            # Doble verificación en memoria por si acaso
            if str(data.get("userId")) != str(usuario_id):
                continue

            # Formatear timestamps
            created = data.get("createdAt")
            if hasattr(created, "isoformat"):
                data["createdAt"] = created.isoformat()
            
            resultados.append({"id": doc.id, **data})

        # Ordenar cronológicamente (más viejos primero para el chat)
        def sort_key(msg):
            ts = msg.get("createdAt")
            return ts if ts else ""

        resultados.sort(key=sort_key)

        print(f"[Chatbot] Se encontraron {len(resultados)} mensajes para el usuario {usuario_id}")
        return {"ok": True, "historial": resultados}
    except Exception as e:
        print(f"[Chatbot] Error crítico en historial: {e}")
        return {"ok": False, "mensaje": str(e)}


@app.get("/api/v1/chatbot/ares/riesgos-detectados/{proyecto_id}")
def obtener_riesgos_detectados(proyecto_id: str, usuario_id: str):
    try:
        cache = obtener_riesgos_detectados_ares(proyecto_id, usuario_id)
        if not cache:
            return {"ok": True, "datos": None}
        return {"ok": True, "datos": cache}
    except Exception as e:
        return {"ok": False, "mensaje": str(e)}


@app.post("/api/v1/chatbot/ares/detectar-riesgos/{proyecto_id}")
def detectar_riesgos_con_ares(proyecto_id: str, usuario_id: str | None = None):
    try:
        from app.model.groq_model import IAAsistente

        deteccion = IAAsistente.detectar_riesgos_emergentes_ares(proyecto_id)
        if "error" in deteccion:
            return {"ok": False, "mensaje": deteccion["error"]}

        if usuario_id and isinstance(deteccion, dict) and isinstance(deteccion.get("riesgos_detectados"), list):
            try:
                riesgos_detectados = []
                for indice, riesgo in enumerate(deteccion.get("riesgos_detectados") or [], start=1):
                    if not isinstance(riesgo, dict):
                        continue
                    riesgo_con_id = dict(riesgo)
                    riesgo_con_id.setdefault("id", f"ia-{indice}")
                    if not riesgo_con_id.get("tipo"):
                        try:
                            probabilidad = int(riesgo_con_id.get("probabilidad") or 0)
                            impacto = int(riesgo_con_id.get("impacto") or 0)
                            score = probabilidad * impacto
                            if score >= 12:
                                riesgo_con_id["tipo"] = "alto"
                            elif score >= 6:
                                riesgo_con_id["tipo"] = "medio"
                            else:
                                riesgo_con_id["tipo"] = "bajo"
                        except Exception:
                            pass
                    riesgos_detectados.append(riesgo_con_id)

                guardar_riesgos_detectados_ares(proyecto_id, usuario_id, riesgos_detectados)
                deteccion["riesgos_detectados"] = riesgos_detectados
            except Exception as cache_error:
                print(f"[AresDetectados] No se pudo guardar cache detectados: {cache_error}")

        return {"ok": True, "datos": deteccion}
    except Exception as e:
        return {"ok": False, "mensaje": str(e)}


@app.get("/api/v1/chatbot/ares/riesgos-personalizados/{proyecto_id}")
def listar_riesgos_personalizados(proyecto_id: str, usuario_id: str):
    try:
        riesgos = listar_riesgos_personalizados_ares(proyecto_id, usuario_id)
        return {"ok": True, "datos": riesgos}
    except Exception as e:
        return {"ok": False, "mensaje": str(e)}


@app.post("/api/v1/chatbot/ares/riesgos-personalizados")
def crear_riesgo_personalizado(payload: RiesgoPersonalizadoRequest):
    try:
        riesgo = crear_riesgo_personalizado_ares(
            payload.proyecto_id,
            payload.usuario_id,
            payload.nombre,
            payload.probabilidad,
            payload.impacto,
            payload.categoria,
            payload.descripcion,
            payload.tratamiento,
        )
        return {"ok": True, "datos": riesgo}
    except Exception as e:
        return {"ok": False, "mensaje": str(e)}


@app.delete("/api/v1/chatbot/ares/riesgos-personalizados/{riesgo_id}")
def eliminar_riesgo_personalizado(
    riesgo_id: str,
    usuario_id: str,
    proyecto_id: str | None = None,
    nombre: str | None = None,
    categoria: str | None = None,
    descripcion: str | None = None,
    tipo: str | None = None,
    probabilidad: int | None = None,
    impacto: int | None = None,
):
    try:
        filtros = {
            "nombre": (nombre or "").strip().lower() or None,
            "categoria": (categoria or "").strip().lower() or None,
            "descripcion": (descripcion or "").strip().lower() or None,
            "tipo": (tipo or "").strip().lower() or None,
            "probabilidad": probabilidad,
            "impacto": impacto,
        }
        filtros = {k: v for k, v in filtros.items() if v is not None}

        eliminado = eliminar_riesgo_personalizado_ares(riesgo_id, usuario_id, proyecto_id, filtros)
        if not eliminado:
            return {"ok": False, "mensaje": "No se encontró el riesgo o no tienes permisos para eliminarlo"}
        return {"ok": True, "datos": eliminado}
    except Exception as e:
        return {"ok": False, "mensaje": str(e)}


@app.post("/api/v1/chat/mensaje")
def enviar_mensaje_chat(payload: ChatMensajeRequest, background_tasks: BackgroundTasks):
    chat_id = (payload.chat_id or "").strip()
    sender_id = (payload.sender_id or "").strip()
    sender_name = (payload.sender_name or "").strip()
    receiver_id = (payload.receiver_id or "").strip()
    receiver_name = (payload.receiver_name or "").strip()
    texto = (payload.texto or "").strip()
    tipo_mensaje = (payload.tipo_mensaje or "texto").strip() or "texto"
    meeting_url = (payload.meeting_url or "").strip() or None
    meeting_title = (payload.meeting_title or "").strip() or None
    meeting_start = (payload.meeting_start or "").strip() or None
    meeting_end = (payload.meeting_end or "").strip() or None
    meeting_details = (payload.meeting_details or "").strip() or None

    if not chat_id or not sender_id or not receiver_id or not texto:
        return {"ok": False, "mensaje": "Faltan datos para enviar el mensaje"}

    if meeting_url and not texto:
        titulo_reunion = meeting_title or "Reunión"
        texto = f"{titulo_reunion}\n{meeting_url}"

    try:
        chat_ref = firestore_db.collection("chats").document(chat_id)
        mensaje_ref = chat_ref.collection("messages").document()
        timestamp = datetime.now(timezone.utc)

        last_message_preview = texto
        if meeting_url:
            titulo_reunion = meeting_title or "Reunión"
            last_message_preview = f"Invitación a reunión: {titulo_reunion}"

        chat_ref.set(
            {
                "participants": [sender_id, receiver_id],
                "participantNames": {
                    sender_id: sender_name,
                    receiver_id: receiver_name,
                },
                "participantPhotos": {
                    sender_id: payload.sender_photo,
                    receiver_id: payload.receiver_photo,
                },
                "updatedAt": timestamp,
                "lastMessage": last_message_preview,
                "lastMessageAt": timestamp,
                "lastSenderId": sender_id,
                "lastSenderName": sender_name,
                "lastSenderPhoto": payload.sender_photo,
                "createdAt": timestamp,
            },
            merge=True,
        )

        mensaje_ref.set(
            {
                "senderId": sender_id,
                "senderName": sender_name,
                "senderPhoto": payload.sender_photo,
                "receiverId": receiver_id,
                "receiverName": receiver_name,
                "receiverPhoto": payload.receiver_photo,
                "texto": texto,
                "tipoMensaje": tipo_mensaje,
                "meetingUrl": meeting_url,
                "meetingTitle": meeting_title,
                "meetingStart": meeting_start,
                "meetingEnd": meeting_end,
                "meetingDetails": meeting_details,
                "createdAt": timestamp,
                "read": False,
            }
        )

        # Enviar notificación por correo al receptor si tiene email.
        # Se hace de forma directa para no depender de BackgroundTasks y tener
        # confirmación inmediata en logs y respuesta de SendGrid.
        try:
            receptor = Usuario_controller.obtener_datos_usuario(receiver_id)
            if receptor and receptor.get("email"):
                correo_receptor = receptor.get("email")
                nombre_receptor = receptor.get("nombre")
                print(f"[Chat] Enviando email a {correo_receptor} por mensaje en chat {chat_id}")
                texto_para_email = texto
                if meeting_url and meeting_url not in texto_para_email:
                    titulo_reunion = meeting_title or "Reunión"
                    texto_para_email = f"{texto_para_email}\n\nEnlace de Google Meet: {meeting_url}\nTítulo: {titulo_reunion}"
                resultado_email = sendgrid_service.send_new_message_email(
                    correo_receptor,
                    nombre_receptor,
                    sender_name,
                    texto_para_email,
                    None,
                )
                print(f"[Chat] Resultado email notificación chat {chat_id}: {resultado_email}")
            else:
                print(f"[Chat] Receptor {receiver_id} sin email; no se envía notificación")
        except Exception as e:
            print(f"[Chat] Error enviando email de notificación: {e}")

        return {"ok": True, "mensaje": "Mensaje enviado", "message_id": mensaje_ref.id}
    except Exception as error:
        return {"ok": False, "mensaje": f"No se pudo enviar el mensaje: {str(error)}"}


class DebugEmailRequest(BaseModel):
    to_email: str
    to_name: str | None = None
    sender_name: str | None = None
    message_text: str | None = None


@app.post("/api/v1/email/debug_send_message")
def debug_send_message(payload: DebugEmailRequest):
    try:
        res = sendgrid_service.send_new_message_email(
            payload.to_email,
            payload.to_name,
            payload.sender_name or "DebugSender",
            payload.message_text or "Prueba de envío desde endpoint debug",
            None,
        )
        return {"ok": True, "resultado": res}
    except Exception as e:
        return {"ok": False, "mensaje": str(e)}


@app.get("/api/v1/email/env")
def debug_email_env():
    try:
        api_key = os.getenv("SENDGRID_API_KEY") or None
        api_suffix = api_key[-4:] if api_key else None
        return {
            "ok": True,
            "from_email": os.getenv("SENDGRID_FROM_EMAIL"),
            "from_name": os.getenv("SENDGRID_FROM_NAME"),
            "api_key_present": bool(api_key),
            "api_key_suffix": api_suffix,
            "logo_url": os.getenv("SENDGRID_LOGO_URL"),
        }
    except Exception as e:
        return {"ok": False, "mensaje": str(e)}


@app.post("/api/v1/email/raw_check")
def raw_sendgrid_check(payload: DebugEmailRequest):
    """Hace una petición HTTP directa a la API v3 de SendGrid con un payload mínimo
    para obtener el status y el body crudo y así diagnosticar errores 401/403/4xx.
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        return {"ok": False, "mensaje": "SENDGRID_API_KEY no está configurada en el entorno"}

    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "personalizations": [{"to": [{"email": payload.to_email, "name": payload.to_name or "Destino"}], "subject": "Prueba raw SendGrid"}],
        "from": {"email": os.getenv("SENDGRID_FROM_EMAIL") or "no-reply@olympo.io", "name": os.getenv("SENDGRID_FROM_NAME") or "Olympo"},
        "content": [{"type": "text/plain", "value": payload.message_text or "Prueba"}],
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        txt = None
        try:
            txt = resp.text
        except Exception:
            txt = str(resp.content)
        return {"ok": True, "status_code": resp.status_code, "headers": dict(resp.headers), "body": txt}
    except Exception as e:
        return {"ok": False, "mensaje": str(e)}


@app.patch("/api/v1/chat/leidos")
def marcar_mensajes_leidos(payload: MarcarLeidosRequest):
    chat_id = (payload.chat_id or "").strip()
    receiver_id = (payload.receiver_id or "").strip()

    if not chat_id or not receiver_id:
        return {"ok": False, "mensaje": "Faltan datos para marcar como leídos"}

    try:
        messages_ref = firestore_db.collection("chats").document(chat_id).collection("messages")
        # Consultamos solo por receiverId para evitar requerir un índice compuesto en Firestore
        query = messages_ref.where("receiverId", "==", receiver_id).stream()
        
        batch = firestore_db.batch()
        count = 0
        for doc in query:
            data = doc.to_dict()
            # Filtramos en memoria los que no han sido leídos
            if data.get("read") is False:
                batch.update(doc.reference, {"read": True})
                count += 1
            
        if count > 0:
            batch.commit()
            
        return {"ok": True, "mensaje": "Mensajes marcados como leídos", "actualizados": count}
    except Exception as error:
        return {"ok": False, "mensaje": f"Error al marcar como leídos: {str(error)}"}

@app.post("/api/v1/proyectos/{proyecto_id}/score")
def obtener_scoring_proyecto(proyecto_id: str):
    try:
        # Primero revisamos si ya existe un análisis en la base de datos
        proyecto = Proyecto_controller.obtener_proyecto(proyecto_id)
        if proyecto and proyecto.get("analisis_ai"):
            print(f"[Scoring] Retornando análisis cacheado para: {proyecto_id}")
            return {"ok": True, "analisis": proyecto["analisis_ai"], "cache": True}

        print(f"[Scoring] No hay caché. Generando nuevo scoring para proyecto: {proyecto_id}")
        analisis = IAAsistente.score_bot(proyecto_id)
        
        if analisis.startswith("Error"):
            return {"ok": False, "mensaje": analisis}
        
        # Guardar el nuevo análisis
        Proyecto_controller.actualizar_analisis_ai(proyecto_id, analisis)
            
        return {"ok": True, "analisis": analisis, "cache": False}
    except Exception as error:
        print(f"[Scoring] Error: {str(error)}")
        return {"ok": False, "mensaje": f"Error al generar scoring: {str(error)}"}


@app.post("/api/v1/ia/optimizar")
def optimizar_con_ia(payload: OptimizarRequest):
    try:
        print(f"[IA] Optimizando descripción para: {payload.titulo}")
        resultado = IAAsistente.optimizar_descripcion(payload.titulo, payload.descripcion)
        
        if resultado.startswith("Error"):
            return {"ok": False, "mensaje": resultado}
            
        return {"ok": True, "descripcion_optimizada": resultado}
    except Exception as error:
        print(f"[IA] Error en optimización: {str(error)}")
        return {"ok": False, "mensaje": f"Error: {str(error)}"}
