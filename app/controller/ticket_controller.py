import uuid
from datetime import datetime, timezone
from typing import List, Optional

import psycopg2

from ..core.neon_conection import PGHOST, PGDATABASE, PGUSER, PGPASSWORD, PGPORT, PGSSLMODE


def _obtener_cursor():
    """Crea una conexión y cursor siguiendo el mismo patrón del proyecto."""
    conexion = psycopg2.connect(
        database=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        host=PGHOST,
        port=PGPORT,
        sslmode=PGSSLMODE,
    )
    return conexion.cursor()


def _asegurar_tabla():
    """Crea la tabla de tickets si no existe."""
    cursor = _obtener_cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id VARCHAR(20) PRIMARY KEY,
                usuario_id VARCHAR(255),
                categoria VARCHAR(100) NOT NULL,
                prioridad VARCHAR(20) NOT NULL DEFAULT 'normal',
                canal VARCHAR(20) NOT NULL DEFAULT 'chat',
                asunto VARCHAR(200) NOT NULL,
                descripcion TEXT NOT NULL,
                adjuntar_contexto BOOLEAN NOT NULL DEFAULT TRUE,
                estado VARCHAR(30) NOT NULL DEFAULT 'nuevo',
                creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                asignado_a VARCHAR(255),
                notas_internas TEXT
            );
            """
        )
        cursor.connection.commit()
    except psycopg2.Error:
        cursor.connection.rollback()
        raise
    finally:
        cursor.close()
        cursor.connection.close()


# Crear la tabla al importar el módulo
try:
    _asegurar_tabla()
except Exception as e:
    print(f"[Tickets] Aviso: no se pudo asegurar la tabla tickets: {e}")


# ---------------------------------------------------------------------------
# Columnas para mapear filas a diccionarios
# ---------------------------------------------------------------------------
_COLUMNAS = [
    "id",
    "usuario_id",
    "categoria",
    "prioridad",
    "canal",
    "asunto",
    "descripcion",
    "adjuntar_contexto",
    "estado",
    "creado_en",
    "actualizado_en",
    "asignado_a",
    "notas_internas",
]


def _fila_a_dict(fila) -> dict | None:
    if fila is None:
        return None
    ticket = dict(zip(_COLUMNAS, fila))
    # Serializar timestamps a ISO string para JSON
    for campo in ("creado_en", "actualizado_en"):
        valor = ticket.get(campo)
        if hasattr(valor, "isoformat"):
            ticket[campo] = valor.isoformat()
    return ticket


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def _generate_id() -> str:
    return f"AMB-{uuid.uuid4().hex[:8].upper()}"


def crear_ticket(data, usuario_id: str | None = None) -> dict:
    """Inserta un nuevo ticket en PostgreSQL."""
    ticket_id = _generate_id()
    ahora = datetime.now(timezone.utc)
    cursor = _obtener_cursor()

    try:
        cursor.execute(
            """
            INSERT INTO tickets
                (id, usuario_id, categoria, prioridad, canal, asunto,
                 descripcion, adjuntar_contexto, estado, creado_en, actualizado_en,
                 asignado_a, notas_internas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, usuario_id, categoria, prioridad, canal, asunto,
                      descripcion, adjuntar_contexto, estado, creado_en,
                      actualizado_en, asignado_a, notas_internas
            """,
            (
                ticket_id,
                usuario_id,
                data.categoria,
                data.prioridad,
                data.canal,
                data.asunto,
                data.descripcion,
                data.adjuntar_contexto,
                "nuevo",
                ahora,
                ahora,
                None,
                None,
            ),
        )
        fila = cursor.fetchone()
        cursor.connection.commit()
        return _fila_a_dict(fila)
    except psycopg2.Error:
        cursor.connection.rollback()
        raise
    finally:
        cursor.close()
        cursor.connection.close()


def obtener_ticket(ticket_id: str) -> Optional[dict]:
    """Obtiene un ticket por su ID."""
    cursor = _obtener_cursor()
    try:
        cursor.execute(
            """
            SELECT id, usuario_id, categoria, prioridad, canal, asunto,
                   descripcion, adjuntar_contexto, estado, creado_en,
                   actualizado_en, asignado_a, notas_internas
            FROM tickets
            WHERE id = %s
            """,
            (ticket_id,),
        )
        fila = cursor.fetchone()
        return _fila_a_dict(fila)
    finally:
        cursor.close()
        cursor.connection.close()


def listar_tickets(filtro: dict = None) -> List[dict]:
    """Lista tickets con filtros opcionales."""
    cursor = _obtener_cursor()
    try:
        # Columnas permitidas para filtrar (evitar inyección SQL)
        columnas_validas = {
            "categoria", "prioridad", "estado", "asignado_a", "canal", "usuario_id"
        }

        base_sql = """
            SELECT id, usuario_id, categoria, prioridad, canal, asunto,
                   descripcion, adjuntar_contexto, estado, creado_en,
                   actualizado_en, asignado_a, notas_internas
            FROM tickets
        """
        params = []

        if filtro:
            condiciones = []
            for clave, valor in filtro.items():
                if valor is not None and clave in columnas_validas:
                    condiciones.append(f"{clave} = %s")
                    params.append(valor)
            if condiciones:
                base_sql += " WHERE " + " AND ".join(condiciones)

        base_sql += " ORDER BY creado_en DESC"

        cursor.execute(base_sql, tuple(params))
        filas = cursor.fetchall()
        return [_fila_a_dict(f) for f in filas]
    finally:
        cursor.close()
        cursor.connection.close()


def actualizar_ticket(ticket_id: str, data) -> Optional[dict]:
    """Actualiza campos de un ticket existente."""
    campos = []
    valores = []

    if data.prioridad is not None:
        campos.append("prioridad = %s")
        valores.append(data.prioridad)
    if data.estado is not None:
        campos.append("estado = %s")
        valores.append(data.estado)
    if data.asignado_a is not None:
        campos.append("asignado_a = %s")
        valores.append(data.asignado_a)
    if data.notas_internas is not None:
        campos.append("notas_internas = %s")
        valores.append(data.notas_internas)

    if not campos:
        return obtener_ticket(ticket_id)

    # Siempre actualizar el timestamp
    campos.append("actualizado_en = %s")
    valores.append(datetime.now(timezone.utc))

    valores.append(ticket_id)

    set_clause = ", ".join(campos)
    update_sql = f"""
        UPDATE tickets SET {set_clause}
        WHERE id = %s
        RETURNING id, usuario_id, categoria, prioridad, canal, asunto,
                  descripcion, adjuntar_contexto, estado, creado_en,
                  actualizado_en, asignado_a, notas_internas
    """

    cursor = _obtener_cursor()
    try:
        cursor.execute(update_sql, tuple(valores))
        fila = cursor.fetchone()
        cursor.connection.commit()
        return _fila_a_dict(fila)
    except psycopg2.Error:
        cursor.connection.rollback()
        raise
    finally:
        cursor.close()
        cursor.connection.close()
