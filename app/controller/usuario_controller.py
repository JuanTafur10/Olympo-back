import psycopg2
from uuid import UUID

from ..core.neon_conection import PGHOST, PGDATABASE, PGUSER, PGPASSWORD, PGPORT, PGSSLMODE


class Usuario_controller:
    @staticmethod
    def _mapear_usuario_fila(fila):
        if fila is None:
            return None

        columnas = [
            "id",
            "firebase_uid",
            "nombre",
            "email",
            "rol",
            "activo",
            "pendiente_aprobacion",
            "telefono",
            "website",
            "linkedin",
            "ciudad",
            "descripcion",
            "creado_en",
            "actualizado_en",
            "foto_perfil",
            "biografia_emprendedor",
            "reputacion_emprendedor",
            "licencias_certificaciones",
            "biografia_inversionista",
            "reputacion_inversionista",
            "intereses_inversion",
            "monto_disponible",
        ]
        return dict(zip(columnas, fila))

    @staticmethod
    def _consultar_usuario(query: str, parametro):
        cursor = Usuario_controller.obtener_cursor()

        try:
            cursor.execute(query, (parametro,))
            fila = cursor.fetchone()
            return Usuario_controller._mapear_usuario_fila(fila)
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def _es_uuid_valido(valor: str | int | None) -> bool:
        if not isinstance(valor, str):
            return False

        try:
            UUID(valor)
            return True
        except Exception:
            return False

    @staticmethod
    def insertar_usuario(rol: str, nombre: str, apellido: str, email: str, firebase_uid: str | None = None):
        cursor = Usuario_controller.obtener_cursor()
        nombre_completo = f"{nombre} {apellido}".strip()

        try:
            cursor.execute(
                """
                INSERT INTO usuarios (nombre, email, rol, activo, firebase_uid)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, firebase_uid, nombre, email, rol, activo
                """,
                (nombre_completo, email, rol, True, firebase_uid),
            )
            usuario_creado = cursor.fetchone()
            cursor.connection.commit()
            return usuario_creado

        except psycopg2.Error:
            cursor.connection.rollback()
            raise

        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def insertar_usuario_con_password(rol: str, nombre_usuario: str, email: str, contraseña_hash: str):
        cursor = Usuario_controller.obtener_cursor()

        try:
            cursor.execute(
                """
                INSERT INTO usuarios (nombre_usuario, email, contraseña_hash, rol, activo)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, nombre_usuario, email, rol, activo
                """,
                (nombre_usuario, email, contraseña_hash, rol, True),
            )
            usuario_creado = cursor.fetchone()
            cursor.connection.commit()
            return usuario_creado

        except psycopg2.Error:
            cursor.connection.rollback()
            raise

        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def insertar_emprendedor(usuario_id: str, biografia: str, licencias_certificaciones: list):
        """Inserta perfil de emprendedor en la tabla emprendedores"""
        cursor = Usuario_controller.obtener_cursor()

        try:
            import json

            cursor.execute(
                """
                INSERT INTO emprendedores (usuario_id, biografia, licencias_certificaciones)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (usuario_id, biografia, json.dumps(licencias_certificaciones)),
            )
            cursor.connection.commit()
            return cursor.fetchone()[0]
        except psycopg2.Error:
            cursor.connection.rollback()
            raise
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def insertar_inversionista(usuario_id: str, biografia: str, intereses_inversion: list, monto_disponible: float = 0):
        """Inserta perfil de inversionista en la tabla inversionistas"""
        cursor = Usuario_controller.obtener_cursor()

        try:
            import json

            cursor.execute(
                """
                INSERT INTO inversionistas (usuario_id, biografia, intereses_inversion, monto_disponible)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (usuario_id, biografia, json.dumps(intereses_inversion), monto_disponible),
            )
            cursor.connection.commit()
            return cursor.fetchone()[0]
        except psycopg2.Error:
            cursor.connection.rollback()
            raise
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def registrar_usuario_completo(
        rol: str,
        nombre: str,
        email: str,
        nombre_usuario: str | None = None,
        firebase_uid: str | None = None,
        activo: bool = True,
        pendiente_aprobacion: bool = False,
        telefono: str | None = None,
        website: str | None = None,
        linkedin: str | None = None,
        ciudad: str | None = None,
        descripcion: str | None = None,
        biografia: str | None = None,
        licencias_certificaciones: list | None = None,
        intereses_inversion: list | None = None,
        monto_disponible: float = 0,
        permitir_admin: bool = False,
    ):
        cursor = Usuario_controller.obtener_cursor()

        try:
            import json

            rol_normalizado = (rol or "").strip().lower()
            nombre_completo = (nombre or nombre_usuario or "").strip()
            nombre_usuario_final = (nombre_usuario or nombre_completo).strip()

            if not nombre_completo:
                raise ValueError("El nombre es obligatorio")

            if not nombre_usuario_final:
                nombre_usuario_final = nombre_completo

            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'usuarios'
                """
            )
            columnas_usuarios = {fila[0] for fila in cursor.fetchall()}
            usa_nombre_usuario = "nombre_usuario" in columnas_usuarios

            columnas_insertar = [
                "nombre",
                "email",
                "rol",
                "activo",
                "pendiente_aprobacion",
                "telefono",
                "website",
                "linkedin",
                "ciudad",
                "descripcion",
                "firebase_uid",
            ]
            valores_insertar = [
                nombre_completo,
                email,
                rol_normalizado,
                activo,
                pendiente_aprobacion,
                telefono,
                website,
                linkedin,
                ciudad,
                descripcion,
                firebase_uid,
            ]

            if usa_nombre_usuario:
                columnas_insertar.insert(0, "nombre_usuario")
                valores_insertar.insert(0, nombre_usuario_final)

            cursor.execute(
                f"""
                INSERT INTO usuarios ({', '.join(columnas_insertar)})
                VALUES ({', '.join(['%s'] * len(columnas_insertar))})
                RETURNING id, firebase_uid, nombre, email, rol, activo, pendiente_aprobacion, telefono, website, linkedin, ciudad, descripcion, creado_en, actualizado_en
                """,
                tuple(valores_insertar),
            )
            usuario_fila = cursor.fetchone()

            if usuario_fila is None:
                raise RuntimeError("No se pudo crear el usuario")

            usuario_id = usuario_fila[0]
            perfil = None

            if rol_normalizado == "emprendedor":
                cursor.execute(
                    """
                    INSERT INTO emprendedores (usuario_id, biografia, licencias_certificaciones)
                    VALUES (%s, %s, %s)
                    RETURNING id, biografia, reputacion, licencias_certificaciones
                    """,
                    (usuario_id, biografia, json.dumps(licencias_certificaciones or [])),
                )
                perfil_fila = cursor.fetchone()
                perfil = {
                    "id": perfil_fila[0],
                    "biografia": perfil_fila[1],
                    "reputacion": perfil_fila[2],
                    "licencias_certificaciones": perfil_fila[3],
                }
            elif rol_normalizado == "inversionista":
                cursor.execute(
                    """
                    INSERT INTO inversionistas (usuario_id, biografia, intereses_inversion, monto_disponible)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, biografia, reputacion, intereses_inversion, monto_disponible
                    """,
                    (usuario_id, biografia, json.dumps(intereses_inversion or []), monto_disponible),
                )
                perfil_fila = cursor.fetchone()
                perfil = {
                    "id": perfil_fila[0],
                    "biografia": perfil_fila[1],
                    "reputacion": perfil_fila[2],
                    "intereses_inversion": perfil_fila[3],
                    "monto_disponible": perfil_fila[4],
                }
            roles_permitidos = {"emprendedor", "inversionista"}
            if permitir_admin:
                roles_permitidos.add("admin")

            if rol_normalizado not in roles_permitidos:
                raise ValueError("Rol de usuario no válido")

            cursor.connection.commit()

            return {
                "usuario": {
                    "id": usuario_fila[0],
                    "firebase_uid": usuario_fila[1],
                    "nombre": usuario_fila[2],
                    "nombre_usuario": nombre_usuario_final,
                    "email": usuario_fila[3],
                    "rol": usuario_fila[4],
                    "activo": usuario_fila[5],
                    "pendiente_aprobacion": usuario_fila[6],
                    "telefono": usuario_fila[7],
                    "website": usuario_fila[8],
                    "linkedin": usuario_fila[9],
                    "ciudad": usuario_fila[10],
                    "descripcion": usuario_fila[11],
                    "creado_en": usuario_fila[12],
                    "actualizado_en": usuario_fila[13],
                },
                "perfil": perfil,
            }

        except psycopg2.Error:
            cursor.connection.rollback()
            raise
        except Exception:
            cursor.connection.rollback()
            raise
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def actualizar_estado_usuario(usuario_id: int | str, activo: bool, pendiente_aprobacion: bool = False):
        cursor = Usuario_controller.obtener_cursor()

        try:
            cursor.execute(
                """
                UPDATE usuarios
                SET activo = %s,
                    pendiente_aprobacion = %s
                WHERE id = %s
                RETURNING id, firebase_uid, nombre, email, rol, activo, pendiente_aprobacion
                """,
                (activo, pendiente_aprobacion, usuario_id),
            )
            usuario_actualizado = cursor.fetchone()
            cursor.connection.commit()
            return usuario_actualizado
        except psycopg2.Error:
            cursor.connection.rollback()
            raise
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def eliminar_usuario_pendiente(usuario_id: int | str):
        cursor = Usuario_controller.obtener_cursor()

        try:
            cursor.execute(
                """
                DELETE FROM usuarios
                WHERE id = %s AND pendiente_aprobacion = TRUE
                RETURNING id, firebase_uid, nombre, email, rol, activo, pendiente_aprobacion
                """,
                (usuario_id,),
            )
            usuario_eliminado = cursor.fetchone()
            cursor.connection.commit()
            return usuario_eliminado
        except psycopg2.Error:
            cursor.connection.rollback()
            raise
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def contar_admins_activos(excluir_usuario_id: int | str | None = None):
        cursor = Usuario_controller.obtener_cursor()

        try:
            if excluir_usuario_id is not None:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM usuarios
                    WHERE rol = 'admin' AND activo = TRUE AND id <> %s
                    """,
                    (excluir_usuario_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM usuarios
                    WHERE rol = 'admin' AND activo = TRUE
                    """
                )

            fila = cursor.fetchone()
            return int(fila[0] or 0) if fila else 0
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def contar_admins_totales():
        cursor = Usuario_controller.obtener_cursor()

        try:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM usuarios
                WHERE rol = 'admin'
                """
            )
            fila = cursor.fetchone()
            return int(fila[0] or 0) if fila else 0
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def _asegurar_tabla_configuracion():
        cursor = Usuario_controller.obtener_cursor()

        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS configuraciones_sistema (
                    clave VARCHAR(120) PRIMARY KEY,
                    valor_bool BOOLEAN NOT NULL DEFAULT TRUE,
                    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                INSERT INTO configuraciones_sistema (clave, valor_bool)
                VALUES ('registro_libre', TRUE)
                ON CONFLICT (clave) DO NOTHING
                """
            )
            cursor.connection.commit()
        except psycopg2.Error:
            cursor.connection.rollback()
            raise
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def obtener_estado_registro_libre() -> bool:
        Usuario_controller._asegurar_tabla_configuracion()
        cursor = Usuario_controller.obtener_cursor()

        try:
            cursor.execute(
                """
                SELECT valor_bool
                FROM configuraciones_sistema
                WHERE clave = 'registro_libre'
                LIMIT 1
                """
            )
            fila = cursor.fetchone()
            return bool(fila[0]) if fila else True
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def actualizar_estado_registro_libre(valor: bool) -> bool:
        Usuario_controller._asegurar_tabla_configuracion()
        cursor = Usuario_controller.obtener_cursor()

        try:
            cursor.execute(
                """
                INSERT INTO configuraciones_sistema (clave, valor_bool)
                VALUES ('registro_libre', %s)
                ON CONFLICT (clave)
                DO UPDATE SET valor_bool = EXCLUDED.valor_bool,
                              actualizado_en = NOW()
                RETURNING valor_bool
                """,
                (valor,),
            )
            fila = cursor.fetchone()
            cursor.connection.commit()
            return bool(fila[0]) if fila else bool(valor)
        except psycopg2.Error:
            cursor.connection.rollback()
            raise
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def listar_usuarios_pendientes_aprobacion(excluir_usuario_id: int | str | None = None):
        cursor = Usuario_controller.obtener_cursor()

        try:
            base_query = """
                SELECT
                    id,
                    firebase_uid,
                    nombre,
                    email,
                    rol,
                    activo,
                    pendiente_aprobacion,
                    telefono,
                    website,
                    linkedin,
                    ciudad,
                    descripcion,
                    creado_en,
                    actualizado_en,
                    foto_perfil
                FROM usuarios
                WHERE pendiente_aprobacion = TRUE
            """
            if excluir_usuario_id:
                base_query += " AND id <> %s"
                cursor.execute(base_query + " ORDER BY creado_en DESC", (excluir_usuario_id,))
            else:
                cursor.execute(base_query + " ORDER BY creado_en DESC")

            columnas = [columna[0] for columna in cursor.description]
            return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def obtener_datos_usuario(usuario_id: int | str):
        if Usuario_controller._es_uuid_valido(usuario_id):
            query = """
            SELECT
                u.id,
                u.firebase_uid,
                u.nombre,
                u.email,
                u.rol,
                u.activo,
                u.pendiente_aprobacion,
                u.telefono,
                u.website,
                u.linkedin,
                u.ciudad,
                u.descripcion,
                u.creado_en,
                u.actualizado_en,
                u.foto_perfil,
                e.biografia AS biografia_emprendedor,
                e.reputacion AS reputacion_emprendedor,
                e.licencias_certificaciones,
                i.biografia AS biografia_inversionista,
                i.reputacion AS reputacion_inversionista,
                i.intereses_inversion,
                i.monto_disponible
            FROM usuarios u
            LEFT JOIN emprendedores e ON e.usuario_id = u.id
            LEFT JOIN inversionistas i ON i.usuario_id = u.id
            WHERE u.id = %s
            LIMIT 1
            """
            usuario = Usuario_controller._consultar_usuario(query, usuario_id)
            if usuario is not None:
                return usuario

        query = """
        SELECT
            u.id,
            u.firebase_uid,
            u.nombre,
            u.email,
            u.rol,
            u.activo,
            u.pendiente_aprobacion,
            u.telefono,
            u.website,
            u.linkedin,
            u.ciudad,
            u.descripcion,
            u.creado_en,
            u.actualizado_en,
            u.foto_perfil,
            e.biografia AS biografia_emprendedor,
            e.reputacion AS reputacion_emprendedor,
            e.licencias_certificaciones,
            i.biografia AS biografia_inversionista,
            i.reputacion AS reputacion_inversionista,
            i.intereses_inversion,
            i.monto_disponible
        FROM usuarios u
        LEFT JOIN emprendedores e ON e.usuario_id = u.id
        LEFT JOIN inversionistas i ON i.usuario_id = u.id
        WHERE u.firebase_uid = %s
        LIMIT 1
        """
        return Usuario_controller._consultar_usuario(query, usuario_id)

    @staticmethod
    def obtener_usuario_por_email(email: str):
        return Usuario_controller._consultar_usuario(
            """
            SELECT
                u.id,
                u.firebase_uid,
                u.nombre,
                u.email,
                u.rol,
                u.activo,
                u.pendiente_aprobacion,
                u.telefono,
                u.website,
                u.linkedin,
                u.ciudad,
                u.descripcion,
                u.creado_en,
                u.actualizado_en,
                u.foto_perfil,
                e.biografia AS biografia_emprendedor,
                e.reputacion AS reputacion_emprendedor,
                e.licencias_certificaciones,
                i.biografia AS biografia_inversionista,
                i.reputacion AS reputacion_inversionista,
                i.intereses_inversion,
                i.monto_disponible
            FROM usuarios u
            LEFT JOIN emprendedores e ON e.usuario_id = u.id
            LEFT JOIN inversionistas i ON i.usuario_id = u.id
            WHERE u.email = %s
            LIMIT 1
            """,
            email,
        )

    @staticmethod
    def listar_usuarios(excluir_usuario_id: int | str | None = None):
        cursor = Usuario_controller.obtener_cursor()

        try:
            cursor.execute(
                """
                SELECT
                    id,
                    firebase_uid,
                    nombre,
                    email,
                    rol,
                    activo,
                    pendiente_aprobacion,
                    telefono,
                    website,
                    linkedin,
                    ciudad,
                    descripcion,
                    creado_en,
                    actualizado_en,
                    foto_perfil
                FROM usuarios
                ORDER BY creado_en DESC
                """
            )

            columnas = [columna[0] for columna in cursor.description]
            usuarios = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

            usuarios_filtrados = [
                usuario
                for usuario in usuarios
                if str(usuario.get("rol") or "").strip().lower() != "admin"
            ]

            if excluir_usuario_id is not None:
                excluir_str = str(excluir_usuario_id)
                usuarios_filtrados = [
                    usuario for usuario in usuarios_filtrados
                    if str(usuario.get("id")) != excluir_str
                ]

            return usuarios_filtrados
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def actualizar_datos_usuario(usuario_id: int | str, telefono: str | None = None, website: str | None = None, linkedin: str | None = None, ciudad: str | None = None, descripcion: str | None = None):
        cursor = Usuario_controller.obtener_cursor()

        try:
            cursor.execute(
                """
                UPDATE usuarios
                SET
                    telefono = COALESCE(%s, telefono),
                    website = COALESCE(%s, website),
                    linkedin = COALESCE(%s, linkedin),
                    ciudad = COALESCE(%s, ciudad),
                    descripcion = COALESCE(%s, descripcion)
                WHERE id = %s
                RETURNING id, telefono, website, linkedin, ciudad, descripcion
                """,
                (telefono, website, linkedin, ciudad, descripcion, usuario_id),
            )
            usuario_actualizado = cursor.fetchone()
            cursor.connection.commit()
            return usuario_actualizado
        except psycopg2.Error:
            cursor.connection.rollback()
            raise
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def actualizar_foto_perfil(usuario_id: int | str, url_foto: str):
        cursor = Usuario_controller.obtener_cursor()
        try:
            cursor.execute(
                """
                UPDATE usuarios
                SET foto_perfil = %s, actualizado_en = NOW()
                WHERE id = %s
                RETURNING id, foto_perfil
                """,
                (url_foto, usuario_id),
            )
            resultado = cursor.fetchone()
            cursor.connection.commit()
            return resultado
        except psycopg2.Error:
            cursor.connection.rollback()
            raise
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def obtener_cursor():
        coneccion = psycopg2.connect(
            database=PGDATABASE,
            user=PGUSER,
            password=PGPASSWORD,
            host=PGHOST,
            port=PGPORT,
            sslmode=PGSSLMODE,
        )
        cursor = coneccion.cursor()
        cursor.execute(
            """
            ALTER TABLE usuarios
            ADD COLUMN IF NOT EXISTS pendiente_aprobacion BOOLEAN NOT NULL DEFAULT FALSE
            """
        )
        coneccion.commit()
        return cursor
