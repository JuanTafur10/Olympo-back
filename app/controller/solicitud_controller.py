import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from ..core.neon_conection import obtener_conexion


def _resolver_inversionista_id(inversionista_id: str):
    """
    Resuelve el ID de perfil de inversionista a partir del ID de inversionista o del ID de usuario.
    Si el usuario no tiene un perfil de inversionista, lo crea automáticamente.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    try:
        # Primero intenta encontrar por ID de inversionista directo
        cursor.execute(
            "SELECT id FROM inversionistas WHERE id = %s",
            (inversionista_id,),
        )
        fila = cursor.fetchone()
        if fila:
            return fila.get("id")

        # Luego intenta encontrar por usuario_id
        cursor.execute(
            "SELECT id FROM inversionistas WHERE usuario_id = %s",
            (inversionista_id,),
        )
        fila = cursor.fetchone()
        if fila:
            return fila.get("id")
        
        # Si no existe, crea automáticamente un perfil de inversionista para este usuario
        print(f"[Solicitud] Creando perfil de inversionista para usuario {inversionista_id}")
        cursor.execute("""
            INSERT INTO inversionistas (usuario_id, biografia, intereses_inversion, monto_disponible)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (inversionista_id, "Inversionista", "[]", 0))
        
        nuevo_inversionista = cursor.fetchone()
        conexion.commit()
        
        if nuevo_inversionista:
            nuevo_id = nuevo_inversionista.get("id")
            print(f"[Solicitud] Perfil de inversionista creado con ID {nuevo_id}")
            return nuevo_id
        
        return None
    finally:
        cursor.close()
        conexion.close()


def crear_solicitud_inversion(proyecto_id: str, inversionista_id: str, monto_solicitado: float, propuesta: str = None):
    """Crea una nueva solicitud de inversión"""
    try:
        conexion_estado = obtener_conexion()
        cursor_estado = conexion_estado.cursor(cursor_factory=RealDictCursor)
        cursor_estado.execute(
            "SELECT id, estado, titulo FROM proyectos WHERE id = %s",
            (proyecto_id,),
        )
        proyecto = cursor_estado.fetchone()
        cursor_estado.close()
        conexion_estado.close()

        if not proyecto:
            raise ValueError("Proyecto no encontrado")

        if str(proyecto.get("estado") or "").lower() != "activo":
            raise ValueError("Este proyecto ya no acepta nuevas solicitudes")

        inversionista_id_real = _resolver_inversionista_id(inversionista_id)
        if not inversionista_id_real:
            raise ValueError("Inversionista no encontrado")

        conexion = obtener_conexion()
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        
        # Insertar la solicitud de inversión
        cursor.execute("""
            INSERT INTO solicitudes_inversion (proyecto_id, inversionista_id, monto_solicitado, propuesta, estado)
            VALUES (%s, %s, %s, %s, 'pendiente')
            RETURNING id, proyecto_id, inversionista_id, monto_solicitado, estado, propuesta, creado_en AS creada_en, actualizado_en AS actualizada_en
        """, (proyecto_id, inversionista_id_real, monto_solicitado, propuesta))
        
        resultado = cursor.fetchone()
        
        # Incrementar el contador de solicitudes en proyectos
        cursor.execute("""
            UPDATE proyectos 
            SET solicitudes = COALESCE(solicitudes, 0) + 1 
            WHERE id = %s
            RETURNING propietario_id, titulo
        """, (proyecto_id,))
        proyecto_info = cursor.fetchone()
        
        conexion.commit()
        
        # Enviar notificación al emprendedor (propietario del proyecto)
        if proyecto_info:
            propietario_id = proyecto_info.get('propietario_id')
            titulo_proyecto = proyecto_info.get('titulo', 'Tu proyecto')
            
            # Importar la función de notificaciones
            from ..core.notificaciones_firestore import crear_notificacion_usuario
            
            try:
                crear_notificacion_usuario(
                    usuario_id=str(propietario_id),
                    tipo="solicitud_inversion",
                    titulo="Nueva solicitud de inversión",
                    mensaje=f"Has recibido una solicitud de inversión para el proyecto '{titulo_proyecto}' por COP${monto_solicitado:,.0f}",
                    ruta_destino="solicitudes",
                    metadata={
                        "proyecto_id": str(proyecto_id),
                        "solicitud_id": str(resultado.get('id')) if resultado else None,
                        "monto": float(monto_solicitado),
                    }
                )
                print(f"[Solicitud] Notificación enviada al emprendedor {propietario_id}")
            except Exception as notif_error:
                print(f"[Solicitud] Advertencia: No se pudo enviar notificación al emprendedor: {notif_error}")
        
        cursor.close()
        conexion.close()
        
        return dict(resultado) if resultado else None
    except Exception as e:
        print(f"[Solicitud] Error al crear solicitud: {e}")
        return None


def listar_solicitudes_por_proyecto(proyecto_id: str):
    """Lista todas las solicitudes de inversión para un proyecto con detalles del inversionista"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                si.id, 
                si.proyecto_id, 
                si.inversionista_id, 
                si.monto_solicitado, 
                si.estado, 
                si.propuesta, 
                si.creado_en AS creada_en, 
                si.actualizado_en AS actualizada_en,
                u.nombre AS inversionista_nombre,
                u.email AS inversionista_email,
                u.telefono AS inversionista_telefono,
                u.linkedin AS inversionista_linkedin,
                u.ciudad AS inversionista_ciudad,
                u.descripcion AS inversionista_descripcion,
                u.foto_perfil AS inversionista_foto_perfil,
                u.firebase_uid AS inversionista_firebase_uid,
                i.usuario_id AS inversionista_usuario_id
            FROM solicitudes_inversion si
            JOIN inversionistas i ON si.inversionista_id = i.id
            JOIN usuarios u ON i.usuario_id = u.id
            WHERE si.proyecto_id = %s
            ORDER BY si.creado_en DESC
        """, (proyecto_id,))
        
        resultados = cursor.fetchall()
        cursor.close()
        conexion.close()

        # Normalizar campos de fecha a ISO strings para evitar problemas de serialización JSON
        procesados = []
        for r in resultados:
            fila = dict(r)
            for campo in ("creada_en", "actualizada_en"):
                val = fila.get(campo)
                try:
                    if hasattr(val, "isoformat"):
                        fila[campo] = val.isoformat()
                except Exception:
                    # dejar el valor original si no se puede convertir
                    pass
            # Añadir campo computado para ID de contacto del inversionista (prioridad: firebase_uid, usuario_id, inversionista_id)
            try:
                fila['inversionista_contacto_id'] = (
                    fila.get('inversionista_firebase_uid') or
                    fila.get('inversionista_usuario_id') or
                    fila.get('inversionista_id')
                )
            except Exception:
                fila['inversionista_contacto_id'] = fila.get('inversionista_id')

            procesados.append(fila)

        print(f"[Solicitud] devolver {len(procesados)} solicitudes (proyecto) - ejemplo fila: {procesados[0] if procesados else 'ninguna'}")
        return procesados
    except Exception as e:
        print(f"[Solicitud] Error al listar solicitudes: {e}")
        return []


def listar_solicitudes_por_inversionista(inversionista_id: str):
    """Lista todas las solicitudes de inversión realizadas por un inversionista con detalles del proyecto y del emprendedor"""
    try:
        inversionista_id_real = _resolver_inversionista_id(inversionista_id)
        if not inversionista_id_real:
            return []

        conexion = obtener_conexion()
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                si.id, 
                si.proyecto_id, 
                si.inversionista_id, 
                si.monto_solicitado, 
                si.estado, 
                si.propuesta, 
                si.creado_en AS creada_en, 
                si.actualizado_en AS actualizada_en,
                p.titulo AS proyecto_nombre,
                u.nombre AS emprendedor_nombre,
                u.email AS emprendedor_email,
                u.telefono AS emprendedor_telefono,
                u.linkedin AS emprendedor_linkedin,
                u.ciudad AS emprendedor_ciudad,
                u.firebase_uid AS emprendedor_firebase_uid,
                p.propietario_id AS emprendedor_usuario_id
            FROM solicitudes_inversion si
            JOIN proyectos p ON si.proyecto_id = p.id
            JOIN usuarios u ON p.propietario_id = u.id
            WHERE si.inversionista_id = %s
            ORDER BY si.creado_en DESC
        """, (inversionista_id_real,))
        
        resultados = cursor.fetchall()
        cursor.close()
        conexion.close()

        # Normalizar campos de fecha a ISO strings para evitar problemas de serialización JSON
        procesados = []
        for r in resultados:
            fila = dict(r)
            for campo in ("creada_en", "actualizada_en"):
                val = fila.get(campo)
                try:
                    if hasattr(val, "isoformat"):
                        fila[campo] = val.isoformat()
                except Exception:
                    pass
            # Añadir campo computado para ID de contacto del emprendedor (prioridad: firebase_uid, usuario_id, propietario_id)
            try:
                fila['emprendedor_contacto_id'] = (
                    fila.get('emprendedor_firebase_uid') or
                    fila.get('emprendedor_usuario_id') or
                    fila.get('propietario_id')
                )
            except Exception:
                fila['emprendedor_contacto_id'] = fila.get('propietario_id')

            procesados.append(fila)

        print(f"[Solicitud] devolver {len(procesados)} solicitudes (inversionista) - ejemplo fila: {procesados[0] if procesados else 'ninguna'}")
        return procesados
    except Exception as e:
        print(f"[Solicitud] Error al listar solicitudes del inversionista: {e}")
        return []


def obtener_solicitud(solicitud_id: str):
    """Obtiene una solicitud específica por ID con detalles cruzados de inversionista y emprendedor"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                si.id, 
                si.proyecto_id, 
                si.inversionista_id, 
                si.monto_solicitado, 
                si.estado, 
                si.propuesta, 
                si.creado_en AS creada_en, 
                si.actualizado_en AS actualizada_en,
                p.titulo AS proyecto_nombre,
                u_inv.nombre AS inversionista_nombre,
                u_inv.email AS inversionista_email,
                u_inv.telefono AS inversionista_telefono,
                u_inv.linkedin AS inversionista_linkedin,
                u_inv.ciudad AS inversionista_ciudad,
                u_inv.descripcion AS inversionista_descripcion,
                u_inv.foto_perfil AS inversionista_foto_perfil,
                u_inv.firebase_uid AS inversionista_firebase_uid,
                inv.usuario_id AS inversionista_usuario_id,
                u_emp.nombre AS emprendedor_nombre,
                u_emp.email AS emprendedor_email,
                u_emp.telefono AS emprendedor_telefono,
                u_emp.linkedin AS emprendedor_linkedin,
                u_emp.ciudad AS emprendedor_ciudad,
                u_emp.firebase_uid AS emprendedor_firebase_uid,
                p.propietario_id AS emprendedor_usuario_id
            FROM solicitudes_inversion si
            JOIN proyectos p ON si.proyecto_id = p.id
            JOIN inversionistas inv ON si.inversionista_id = inv.id
            JOIN usuarios u_inv ON inv.usuario_id = u_inv.id
            JOIN usuarios u_emp ON p.propietario_id = u_emp.id
            WHERE si.id = %s
        """, (solicitud_id,))
        
        resultado = cursor.fetchone()
        cursor.close()
        conexion.close()
        if not resultado:
            return None

        fila = dict(resultado)
        # Normalizar fechas
        for campo in ("creada_en", "actualizada_en"):
            val = fila.get(campo)
            try:
                if hasattr(val, "isoformat"):
                    fila[campo] = val.isoformat()
            except Exception:
                pass

        # Añadir campos computados de contacto
        try:
            fila['inversionista_contacto_id'] = (
                fila.get('inversionista_firebase_uid') or
                fila.get('inversionista_usuario_id') or
                fila.get('inversionista_id')
            )
        except Exception:
            fila['inversionista_contacto_id'] = fila.get('inversionista_id')

        try:
            fila['emprendedor_contacto_id'] = (
                fila.get('emprendedor_firebase_uid') or
                fila.get('emprendedor_usuario_id') or
                fila.get('propietario_id')
            )
        except Exception:
            fila['emprendedor_contacto_id'] = fila.get('propietario_id')

        return fila
    except Exception as e:
        print(f"[Solicitud] Error al obtener solicitud: {e}")
        return None


def actualizar_estado_solicitud(solicitud_id: str, nuevo_estado: str):
    """Actualiza el estado de una solicitud (pendiente, aceptada, rechazada, retirada)"""
    print(f"[actualizar_estado_solicitud] INICIO - solicitud_id={solicitud_id}, nuevo_estado={nuevo_estado}")
    
    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        print(f"[actualizar_estado_solicitud] Conexión abierta")
        
        cursor = conexion.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT 
                si.id,
                si.proyecto_id,
                si.inversionista_id,
                si.monto_solicitado,
                p.titulo AS proyecto_titulo,
                p.estado AS proyecto_estado,
                i.usuario_id AS inversionista_usuario_id
            FROM solicitudes_inversion si
            JOIN proyectos p ON si.proyecto_id = p.id
            JOIN inversionistas i ON si.inversionista_id = i.id
            WHERE si.id = %s
            """,
            (solicitud_id,),
        )
        solicitud_info = cursor.fetchone()

        if not solicitud_info:
            print(f"[actualizar_estado_solicitud] ❌ Solicitud no encontrada")
            cursor.close()
            conexion.close()
            return None

        proyecto_estado_actual = str(solicitud_info.get("proyecto_estado") or "").lower()
        if nuevo_estado == "aceptada" and proyecto_estado_actual != "activo":
            print(f"[actualizar_estado_solicitud] ❌ El proyecto ya no está activo")
            cursor.close()
            conexion.close()
            return None
        
        # UPDATE directo sin JOIN
        print(f"[actualizar_estado_solicitud] Ejecutando UPDATE simple...")
        cursor.execute("""
            UPDATE solicitudes_inversion
            SET estado = %s, actualizado_en = NOW()
            WHERE id = %s
            RETURNING id, estado
        """, (nuevo_estado, solicitud_id))
        
        resultado = cursor.fetchone()
        print(f"[actualizar_estado_solicitud] UPDATE resultado (raw): {resultado}")
        print(f"[actualizar_estado_solicitud] UPDATE resultado type: {type(resultado)}")

        # Ensure the status update is persisted even if no further DB work is done
        try:
            conexion.commit()
            print("[actualizar_estado_solicitud] Commit after status update")
        except Exception as e:
            print(f"[actualizar_estado_solicitud] Warning: commit failed after update: {e}")
        
        if resultado:
            print(f"[actualizar_estado_solicitud] Resultado encontrado, convirtiendo a dict...")
            resultado_dict = dict(resultado)
            print(f"[actualizar_estado_solicitud] Resultado dict: {resultado_dict}")
        else:
            print(f"[actualizar_estado_solicitud] ❌ Resultado es None - UPDATE no retornó datos")
            resultado_dict = None
        
        if nuevo_estado == "aceptada":
            cursor.execute(
                """
                INSERT INTO inversiones (proyecto_id, inversionista_id, monto, moneda, porcentaje_participacion, notas)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    solicitud_info.get("proyecto_id"),
                    solicitud_info.get("inversionista_id"),
                    solicitud_info.get("monto_solicitado"),
                    "COP",
                    None,
                    None,
                ),
            )
            cursor.execute(
                """
                UPDATE proyectos
                SET estado = 'inactivo', actualizado_en = NOW()
                WHERE id = %s
                """,
                (solicitud_info.get("proyecto_id"),),
            )
            print(f"[actualizar_estado_solicitud] Proyecto marcado como inactivo y inversión registrada")

            conexion.commit()
            print(f"[actualizar_estado_solicitud] COMMIT realizado")
        
        cursor.close()
        conexion.close()
        print(f"[actualizar_estado_solicitud] Conexión cerrada")
        
        # Enviar notificación si fue exitoso
        if resultado_dict and nuevo_estado in ['aceptada', 'rechazada']:
            print(f"[actualizar_estado_solicitud] Intentando enviar notificación...")
            if solicitud_info:
                inversionista_usuario_id = solicitud_info.get('inversionista_usuario_id')
                proyecto_titulo = solicitud_info.get('proyecto_titulo', 'Tu proyecto')
                monto = solicitud_info.get('monto_solicitado', 0)
                
                from ..core.notificaciones_firestore import crear_notificacion_usuario
                
                try:
                    if nuevo_estado == 'aceptada':
                        mensaje = f"Tu solicitud de inversión para '{proyecto_titulo}' por COP${monto:,.0f} ha sido ACEPTADA ✅"
                        tipo_notif = "solicitud_aceptada"
                    else:
                        mensaje = f"Tu solicitud de inversión para '{proyecto_titulo}' por COP${monto:,.0f} ha sido RECHAZADA ❌"
                        tipo_notif = "solicitud_rechazada"
                    
                    crear_notificacion_usuario(
                        usuario_id=str(inversionista_usuario_id),
                        tipo=tipo_notif,
                        titulo=f"Solicitud {nuevo_estado.capitalize()}",
                        mensaje=mensaje,
                        ruta_destino="solicitudes",
                        metadata={
                            "proyecto_id": str(solicitud_info.get('proyecto_id')),
                            "solicitud_id": str(solicitud_id),
                            "monto": float(monto),
                        }
                    )
                    print(f"[actualizar_estado_solicitud] ✅ Notificación enviada")
                except Exception as notif_error:
                    print(f"[actualizar_estado_solicitud] ⚠️ Error notificación: {notif_error}")

        # Añadir información útil al resultado para que el caller pueda notificar por email
        try:
            if resultado_dict and solicitud_info:
                resultado_dict["inversionista_usuario_id"] = solicitud_info.get("inversionista_usuario_id")
                resultado_dict["proyecto_titulo"] = solicitud_info.get("proyecto_titulo")
                resultado_dict["monto_solicitado"] = solicitud_info.get("monto_solicitado")
        except Exception:
            pass
        
        print(f"[actualizar_estado_solicitud] RETORNANDO: {resultado_dict}")
        return resultado_dict
        
    except Exception as e:
        print(f"[actualizar_estado_solicitud] ❌ EXCEPCIÓN: {e}")
        import traceback
        traceback.print_exc()
        try:
            conexion.rollback()
        except Exception:
            pass
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conexion.close()
        except Exception:
            pass
        return None


def eliminar_solicitud(solicitud_id: str):
    """Elimina una solicitud de inversión"""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Obtener el proyecto_id antes de eliminar para decrementar el contador
        cursor.execute("SELECT proyecto_id FROM solicitudes_inversion WHERE id = %s", (solicitud_id,))
        fila = cursor.fetchone()
        
        cursor.execute("""
            DELETE FROM solicitudes_inversion
            WHERE id = %s
        """, (solicitud_id,))
        
        if fila:
            proyecto_id = fila[0]
            cursor.execute("""
                UPDATE proyectos 
                SET solicitudes = GREATEST(0, solicitudes - 1) 
                WHERE id = %s
            """, (proyecto_id,))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        
        return True
    except Exception as e:
        print(f"[Solicitud] Error al eliminar solicitud: {e}")
        return False
