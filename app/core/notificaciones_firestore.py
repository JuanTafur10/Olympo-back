from datetime import datetime, timezone

from .firebase_conection import firestore_db


def crear_notificacion_usuario(
    usuario_id: str,
    tipo: str,
    titulo: str,
    mensaje: str = "",
    ruta_destino: str | None = None,
    metadata: dict | None = None,
):
    if not usuario_id:
        return None

    if str(tipo or "").strip() == "mensaje":
        print(f"[Notificaciones] Guardado omitido para tipo mensaje del usuario: {usuario_id}")
        return None

    documento = {
        "usuario_id": str(usuario_id),
        "tipo": str(tipo or "info"),
        "titulo": str(titulo or ""),
        "mensaje": str(mensaje or ""),
        "ruta_destino": ruta_destino,
        "metadata": metadata or {},
        "leida": False,
        "eliminada": False,
        "creada_en": datetime.now(timezone.utc),
        "actualizada_en": datetime.now(timezone.utc),
    }

    try:
        doc_id, doc_ref = firestore_db.collection("notificaciones").add(documento)
        print(f"[Notificaciones] Notificación guardada en Firestore con ID: {doc_id}")
        return doc_id
    except Exception as e:
        print(f"[Notificaciones] Error al crear notificación: {e}")
        return None


def listar_notificaciones_usuario(usuario_id: str):
    if not usuario_id:
        return []

    try:
        query = (
            firestore_db.collection("notificaciones")
            .where("usuario_id", "==", str(usuario_id))
            .where("eliminada", "==", False)
            .stream()
        )

        resultados = []
        for doc in query:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            resultados.append(data)

        resultados.sort(key=lambda item: item.get("creada_en") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return resultados
    except Exception:
        return []


def marcar_notificacion_leida(notification_id: str):
    if not notification_id:
        return False

    try:
        firestore_db.collection("notificaciones").document(notification_id).set(
            {"leida": True, "actualizada_en": datetime.now(timezone.utc)},
            merge=True,
        )
        return True
    except Exception:
        return False


def marcar_todas_notificaciones_leidas(usuario_id: str):
    if not usuario_id:
        return 0

    try:
        query = (
            firestore_db.collection("notificaciones")
            .where("usuario_id", "==", str(usuario_id))
            .where("eliminada", "==", False)
            .stream()
        )

        batch = firestore_db.batch()
        count = 0
        for doc in query:
            data = doc.to_dict() or {}
            if not data.get("leida"):
                batch.update(doc.reference, {"leida": True, "actualizada_en": datetime.now(timezone.utc)})
                count += 1

        if count > 0:
          batch.commit()
        return count
    except Exception:
        return 0


def eliminar_notificacion(notification_id: str):
    if not notification_id:
        return False

    try:
        firestore_db.collection("notificaciones").document(notification_id).delete()
        return True
    except Exception:
        return False
