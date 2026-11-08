from uuid import UUID

from psycopg2.extras import RealDictCursor, Json

from ..core.neon_conection import obtener_conexion


def _asegurar_tabla_cache_ares(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ares_riesgos_cache (
            proyecto_id UUID NOT NULL,
            usuario_id TEXT NOT NULL,
            riesgos JSONB NOT NULL,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (proyecto_id, usuario_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ares_cache_actualizado_en
        ON ares_riesgos_cache(actualizado_en DESC)
        """
    )


def _asegurar_tabla_riesgos_detectados(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ares_riesgos_detectados (
            proyecto_id UUID NOT NULL,
            usuario_id TEXT NOT NULL,
            riesgos JSONB NOT NULL,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (proyecto_id, usuario_id)
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ares_detectados_actualizado_en
        ON ares_riesgos_detectados(actualizado_en DESC)
        """
    )


def _asegurar_tabla_riesgos_personalizados(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ares_riesgos_personalizados (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            proyecto_id UUID NOT NULL,
            usuario_id TEXT NOT NULL,
            categoria TEXT NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            probabilidad INTEGER NOT NULL CHECK (probabilidad BETWEEN 1 AND 5),
            impacto INTEGER NOT NULL CHECK (impacto BETWEEN 1 AND 5),
            tratamiento TEXT,
            tipo TEXT NOT NULL,
            es_personalizado BOOLEAN NOT NULL DEFAULT TRUE,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_ares_personalizados_proyecto
                FOREIGN KEY (proyecto_id)
                REFERENCES proyectos(id)
                ON DELETE CASCADE
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ares_personalizados_proyecto_usuario
        ON ares_riesgos_personalizados(proyecto_id, usuario_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ares_personalizados_tipo
        ON ares_riesgos_personalizados(tipo)
        """
    )


def _asegurar_tabla_riesgos_eliminados(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ares_riesgos_eliminados (
            proyecto_id UUID NOT NULL,
            usuario_id TEXT NOT NULL,
            firma TEXT NOT NULL,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (proyecto_id, usuario_id, firma)
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ares_eliminados_proyecto_usuario
        ON ares_riesgos_eliminados(proyecto_id, usuario_id)
        """
    )


def obtener_cache_riesgos_ares(proyecto_id: str, usuario_id: str):
    if not proyecto_id or not usuario_id:
        return None

    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    try:
        _asegurar_tabla_cache_ares(cursor)
        _asegurar_tabla_riesgos_eliminados(cursor)
        cursor.execute(
            """
            SELECT proyecto_id, usuario_id, riesgos, creado_en, actualizado_en
            FROM ares_riesgos_cache
            WHERE proyecto_id = %s AND usuario_id = %s
            """,
            (proyecto_id, str(usuario_id)),
        )
        fila = cursor.fetchone()
        if not fila:
            conexion.commit()
            return None

        resultado = dict(fila)
        resultado["riesgos"], _ = _filtrar_riesgos_excluidos(cursor, proyecto_id, usuario_id, resultado.get("riesgos") or [])
        for campo in ("creado_en", "actualizado_en"):
            valor = resultado.get(campo)
            if hasattr(valor, "isoformat"):
                resultado[campo] = valor.isoformat()

        conexion.commit()
        return resultado
    finally:
        cursor.close()
        conexion.close()


def guardar_cache_riesgos_ares(proyecto_id: str, usuario_id: str, riesgos):
    if not proyecto_id or not usuario_id:
        return None

    if not isinstance(riesgos, list):
        raise ValueError("El campo 'riesgos' debe ser una lista")

    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    try:
        _asegurar_tabla_cache_ares(cursor)
        _asegurar_tabla_riesgos_eliminados(cursor)
        riesgos, _ = _filtrar_riesgos_excluidos(cursor, proyecto_id, usuario_id, riesgos)
        cursor.execute(
            """
            INSERT INTO ares_riesgos_cache (proyecto_id, usuario_id, riesgos)
            VALUES (%s, %s, %s)
            ON CONFLICT (proyecto_id, usuario_id)
            DO UPDATE SET
                riesgos = EXCLUDED.riesgos,
                actualizado_en = NOW()
            RETURNING proyecto_id, usuario_id, riesgos, creado_en, actualizado_en
            """,
            (proyecto_id, str(usuario_id), Json(riesgos)),
        )
        fila = cursor.fetchone()
        conexion.commit()

        resultado = dict(fila) if fila else None
        if not resultado:
            return None

        for campo in ("creado_en", "actualizado_en"):
            valor = resultado.get(campo)
            if hasattr(valor, "isoformat"):
                resultado[campo] = valor.isoformat()

        return resultado
    finally:
        cursor.close()
        conexion.close()


def obtener_riesgos_detectados_ares(proyecto_id: str, usuario_id: str):
    if not proyecto_id or not usuario_id:
        return None

    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    try:
        _asegurar_tabla_riesgos_detectados(cursor)
        _asegurar_tabla_riesgos_eliminados(cursor)
        cursor.execute(
            """
            SELECT proyecto_id, usuario_id, riesgos, creado_en, actualizado_en
            FROM ares_riesgos_detectados
            WHERE proyecto_id = %s AND usuario_id = %s
            """,
            (proyecto_id, str(usuario_id)),
        )
        fila = cursor.fetchone()
        if not fila:
            conexion.commit()
            return None

        resultado = dict(fila)
        resultado["riesgos"], _ = _filtrar_riesgos_excluidos(cursor, proyecto_id, usuario_id, resultado.get("riesgos") or [])
        for campo in ("creado_en", "actualizado_en"):
            valor = resultado.get(campo)
            if hasattr(valor, "isoformat"):
                resultado[campo] = valor.isoformat()

        conexion.commit()
        return resultado
    finally:
        cursor.close()
        conexion.close()


def guardar_riesgos_detectados_ares(proyecto_id: str, usuario_id: str, riesgos):
    if not proyecto_id or not usuario_id:
        return None

    if not isinstance(riesgos, list):
        raise ValueError("El campo 'riesgos' debe ser una lista")

    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    try:
        _asegurar_tabla_riesgos_detectados(cursor)
        _asegurar_tabla_riesgos_eliminados(cursor)
        riesgos, _ = _filtrar_riesgos_excluidos(cursor, proyecto_id, usuario_id, riesgos)
        cursor.execute(
            """
            INSERT INTO ares_riesgos_detectados (proyecto_id, usuario_id, riesgos)
            VALUES (%s, %s, %s)
            ON CONFLICT (proyecto_id, usuario_id)
            DO UPDATE SET
                riesgos = EXCLUDED.riesgos,
                actualizado_en = NOW()
            RETURNING proyecto_id, usuario_id, riesgos, creado_en, actualizado_en
            """,
            (proyecto_id, str(usuario_id), Json(riesgos)),
        )
        fila = cursor.fetchone()
        conexion.commit()

        resultado = dict(fila) if fila else None
        if not resultado:
            return None

        for campo in ("creado_en", "actualizado_en"):
            valor = resultado.get(campo)
            if hasattr(valor, "isoformat"):
                resultado[campo] = valor.isoformat()

        return resultado
    finally:
        cursor.close()
        conexion.close()


def _calcular_tipo_riesgo(probabilidad: int, impacto: int) -> str:
    score = probabilidad * impacto
    if score >= 12:
        return "alto"
    if score >= 6:
        return "medio"
    return "bajo"


def listar_riesgos_personalizados_ares(proyecto_id: str, usuario_id: str):
    if not proyecto_id or not usuario_id:
        return []

    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    try:
        _asegurar_tabla_riesgos_personalizados(cursor)
        cursor.execute(
            """
            SELECT id, proyecto_id, usuario_id, categoria, nombre, descripcion,
                   probabilidad, impacto, tratamiento, tipo, es_personalizado,
                   creado_en, actualizado_en
            FROM ares_riesgos_personalizados
            WHERE proyecto_id = %s AND usuario_id = %s
            ORDER BY creado_en DESC
            """,
            (proyecto_id, str(usuario_id)),
        )
        resultados = cursor.fetchall() or []
        procesados = []
        for fila in resultados:
            data = dict(fila)
            for campo in ("creado_en", "actualizado_en"):
                valor = data.get(campo)
                if hasattr(valor, "isoformat"):
                    data[campo] = valor.isoformat()
            procesados.append(data)

        conexion.commit()
        return procesados
    finally:
        cursor.close()
        conexion.close()


def crear_riesgo_personalizado_ares(
    proyecto_id: str,
    usuario_id: str,
    nombre: str,
    probabilidad: int,
    impacto: int,
    categoria: str | None = None,
    descripcion: str | None = None,
    tratamiento: str | None = None,
):
    if not proyecto_id or not usuario_id:
        raise ValueError("Faltan datos para crear el riesgo")

    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nombre del riesgo es obligatorio")

    probabilidad = max(1, min(5, int(probabilidad)))
    impacto = max(1, min(5, int(impacto)))
    categoria = (categoria or "Usuario").strip() or "Usuario"
    descripcion = (descripcion or "").strip() or "Riesgo creado manualmente por el usuario."
    tratamiento = (tratamiento or "").strip() or "Definir un plan de mitigación para este riesgo."
    tipo = _calcular_tipo_riesgo(probabilidad, impacto)

    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    try:
        _asegurar_tabla_riesgos_personalizados(cursor)
        cursor.execute(
            """
            INSERT INTO ares_riesgos_personalizados (
                proyecto_id, usuario_id, categoria, nombre, descripcion,
                probabilidad, impacto, tratamiento, tipo
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, proyecto_id, usuario_id, categoria, nombre, descripcion,
                      probabilidad, impacto, tratamiento, tipo, es_personalizado,
                      creado_en, actualizado_en
            """,
            (
                proyecto_id,
                str(usuario_id),
                categoria,
                nombre,
                descripcion,
                probabilidad,
                impacto,
                tratamiento,
                tipo,
            ),
        )
        fila = cursor.fetchone()
        conexion.commit()

        resultado = dict(fila) if fila else None
        if not resultado:
            return None

        for campo in ("creado_en", "actualizado_en"):
            valor = resultado.get(campo)
            if hasattr(valor, "isoformat"):
                resultado[campo] = valor.isoformat()

        return resultado
    finally:
        cursor.close()
        conexion.close()


def _filtrar_riesgos_por_id(riesgos, riesgo_id: str):
    if not isinstance(riesgos, list):
        return [], False

    riesgo_id_str = str(riesgo_id)
    indice_objetivo = None
    if riesgo_id_str.startswith("ia-") or riesgo_id_str.startswith("usr-"):
        try:
            indice_objetivo = max(1, int(riesgo_id_str.split("-", 1)[1])) - 1
        except Exception:
            indice_objetivo = None

    restantes = []
    eliminado = False
    for idx, riesgo in enumerate(riesgos):
      if str(riesgo.get("id") or riesgo.get("riesgo_id") or "") == riesgo_id_str:
          eliminado = True
          continue
      if indice_objetivo is not None and idx == indice_objetivo and not (riesgo.get("id") or riesgo.get("riesgo_id")):
          eliminado = True
          continue
      restantes.append(riesgo)
    return restantes, eliminado


def _normalizar_texto(valor):
    return str(valor or "").strip().lower()


def _calcular_tipo_desde_valores(probabilidad, impacto):
    try:
        score = int(probabilidad or 0) * int(impacto or 0)
    except Exception:
        return None
    if score >= 12:
        return "alto"
    if score >= 6:
        return "medio"
    return "bajo"


def _coincide_riesgo(riesgo, filtros: dict):
    if not isinstance(riesgo, dict):
        return False

    if filtros.get("nombre") and _normalizar_texto(riesgo.get("nombre")) != filtros["nombre"]:
        return False
    if filtros.get("categoria") and _normalizar_texto(riesgo.get("categoria")) != filtros["categoria"]:
        return False
    if filtros.get("tipo") and _normalizar_texto(riesgo.get("tipo")) != filtros["tipo"]:
        tipo_guardado = _normalizar_texto(riesgo.get("tipo"))
        if not tipo_guardado:
            tipo_guardado = _calcular_tipo_desde_valores(riesgo.get("probabilidad"), riesgo.get("impacto"))
        if _normalizar_texto(tipo_guardado) != filtros["tipo"]:
            return False
    if not filtros.get("nombre") and filtros.get("descripcion") and _normalizar_texto(riesgo.get("descripcion")) != filtros["descripcion"]:
        return False

    if filtros.get("probabilidad") is not None:
        try:
            if int(riesgo.get("probabilidad") or 0) != int(filtros["probabilidad"]):
                return False
        except Exception:
            return False

    if filtros.get("impacto") is not None:
        try:
            if int(riesgo.get("impacto") or 0) != int(filtros["impacto"]):
                return False
        except Exception:
            return False

    return True


def _firma_riesgo(riesgo: dict | None) -> str:
    if not isinstance(riesgo, dict):
        return ""
    def _pieza_numero(valor):
        try:
            return str(int(valor))
        except Exception:
            return ""

    partes = [
        _normalizar_texto(riesgo.get("nombre")),
        _normalizar_texto(riesgo.get("categoria")),
        _normalizar_texto(riesgo.get("tipo")),
        _pieza_numero(riesgo.get("probabilidad")),
        _pieza_numero(riesgo.get("impacto")),
    ]
    return "|".join(partes)


def _obtener_firmas_eliminadas(cursor, proyecto_id: str, usuario_id: str):
    cursor.execute(
        """
        SELECT firma
        FROM ares_riesgos_eliminados
        WHERE proyecto_id = %s AND usuario_id = %s
        """,
        (proyecto_id, str(usuario_id)),
    )
    filas = cursor.fetchall() or []
    return {str(fila.get("firma") or "") for fila in filas if str(fila.get("firma") or "").strip()}


def _filtrar_riesgos_excluidos(cursor, proyecto_id: str, usuario_id: str, riesgos):
    if not isinstance(riesgos, list) or not proyecto_id or not usuario_id:
        return riesgos, False

    firmas_eliminadas = _obtener_firmas_eliminadas(cursor, proyecto_id, usuario_id)
    if not firmas_eliminadas:
        return riesgos, False

    filtrados = []
    eliminado = False
    for riesgo in riesgos:
        firma = _firma_riesgo(riesgo)
        if firma and firma in firmas_eliminadas:
            eliminado = True
            continue
        filtrados.append(riesgo)
    return filtrados, eliminado


def _registrar_riesgo_eliminado(cursor, proyecto_id: str, usuario_id: str, riesgo: dict | None):
    firma = _firma_riesgo(riesgo)
    if not firma or not proyecto_id or not usuario_id:
        return

    cursor.execute(
        """
        INSERT INTO ares_riesgos_eliminados (proyecto_id, usuario_id, firma)
        VALUES (%s, %s, %s)
        ON CONFLICT (proyecto_id, usuario_id, firma)
        DO NOTHING
        """,
        (proyecto_id, str(usuario_id), firma),
    )


def _filtrar_riesgos_por_filtros(riesgos, filtros: dict):
    if not isinstance(riesgos, list) or not filtros:
        return [], False

    restantes = []
    eliminado = False
    for riesgo in riesgos:
        if _coincide_riesgo(riesgo, filtros):
            eliminado = True
            continue
        restantes.append(riesgo)
    return restantes, eliminado


def _actualizar_lista_jsonb(cursor, tabla: str, proyecto_id: str, usuario_id: str, riesgo_id: str, filtros: dict | None = None):
    cursor.execute(
        f"""
        SELECT riesgos
        FROM {tabla}
        WHERE proyecto_id = %s AND usuario_id = %s
        FOR UPDATE
        """,
        (proyecto_id, str(usuario_id)),
    )
    fila = cursor.fetchone()
    if not fila:
        return False

    riesgos_actuales = fila.get("riesgos") or []
    riesgos_filtrados, eliminado = _filtrar_riesgos_por_id(riesgos_actuales, riesgo_id)
    if not eliminado and filtros:
        riesgos_filtrados, eliminado = _filtrar_riesgos_por_filtros(riesgos_actuales, filtros)
    if not eliminado:
        return False

    if riesgos_filtrados:
        cursor.execute(
            f"""
            UPDATE {tabla}
            SET riesgos = %s,
                actualizado_en = NOW()
            WHERE proyecto_id = %s AND usuario_id = %s
            """,
            (Json(riesgos_filtrados), proyecto_id, str(usuario_id)),
        )
    else:
        cursor.execute(
            f"""
            DELETE FROM {tabla}
            WHERE proyecto_id = %s AND usuario_id = %s
            """,
            (proyecto_id, str(usuario_id)),
        )

    return True


def _es_uuid_valido(valor: str) -> bool:
    try:
        UUID(str(valor))
        return True
    except Exception:
        return False


def eliminar_riesgo_personalizado_ares(
    riesgo_id: str,
    usuario_id: str,
    proyecto_id: str | None = None,
    filtros: dict | None = None,
):
    return eliminar_riesgo_ares(riesgo_id, usuario_id, proyecto_id, filtros)


def eliminar_riesgo_ares(riesgo_id: str, usuario_id: str, proyecto_id: str | None = None, filtros: dict | None = None):
    if not riesgo_id or not usuario_id:
        return None

    if not proyecto_id:
        return None

    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=RealDictCursor)
    try:
        _asegurar_tabla_cache_ares(cursor)
        _asegurar_tabla_riesgos_detectados(cursor)
        _asegurar_tabla_riesgos_personalizados(cursor)

        fila_personal = None
        if _es_uuid_valido(riesgo_id):
            cursor.execute(
                """
                DELETE FROM ares_riesgos_personalizados
                WHERE id = %s AND usuario_id = %s AND proyecto_id = %s
                RETURNING id, proyecto_id, usuario_id
                """,
                (riesgo_id, str(usuario_id), proyecto_id),
            )
            fila_personal = cursor.fetchone()

        if fila_personal:
            _actualizar_lista_jsonb(cursor, "ares_riesgos_detectados", proyecto_id, usuario_id, riesgo_id, filtros)
            _actualizar_lista_jsonb(cursor, "ares_riesgos_cache", proyecto_id, usuario_id, riesgo_id, filtros)
            conexion.commit()
            return {"tipo": "personalizado", **dict(fila_personal)}

        eliminado_detectado = _actualizar_lista_jsonb(cursor, "ares_riesgos_detectados", proyecto_id, usuario_id, riesgo_id, filtros)
        eliminado_cache = _actualizar_lista_jsonb(cursor, "ares_riesgos_cache", proyecto_id, usuario_id, riesgo_id, filtros)

        # Si la eliminación afectó a cache o detectados, registrar la firma
        if (eliminado_detectado or eliminado_cache) and not _es_uuid_valido(riesgo_id):
            _registrar_riesgo_eliminado(cursor, proyecto_id, usuario_id, filtros)

        # Si no se encontró en las listas pero se pasaron filtros válidos, intentar
        # registrar la firma basada en los filtros para ocultarlo en futuras lecturas
        if not eliminado_detectado and not eliminado_cache and filtros and not _es_uuid_valido(riesgo_id):
            posible_riesgo = {
                "nombre": filtros.get("nombre"),
                "categoria": filtros.get("categoria"),
                "tipo": filtros.get("tipo"),
                "probabilidad": filtros.get("probabilidad"),
                "impacto": filtros.get("impacto"),
            }
            _registrar_riesgo_eliminado(cursor, proyecto_id, usuario_id, posible_riesgo)
            conexion.commit()
            return {
                "tipo": "detectado",
                "riesgo_id": riesgo_id,
                "proyecto_id": proyecto_id,
                "usuario_id": str(usuario_id),
                "not_found_but_hidden": True,
            }

        if not eliminado_detectado and not eliminado_cache:
            conexion.commit()
            return None

        conexion.commit()
        return {
            "tipo": "detectado",
            "riesgo_id": riesgo_id,
            "proyecto_id": proyecto_id,
            "usuario_id": str(usuario_id),
        }
    finally:
        cursor.close()
        conexion.close()
