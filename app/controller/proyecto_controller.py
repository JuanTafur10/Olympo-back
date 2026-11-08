from decimal import Decimal, InvalidOperation

import psycopg2

from ..core.neon_conection import PGHOST, PGDATABASE, PGUSER, PGPASSWORD, PGPORT, PGSSLMODE

class Proyecto_controller:
    @staticmethod
    def insertar_proyecto(propietario_id, titulo: str, descripcion: str, presupuesto: float, estado: str, fecha_publicacion: str):
        cursor = Proyecto_controller.obtener_cursor()
        try:
            try:
                presupuesto_decimal = Decimal(str(presupuesto)).quantize(Decimal("0.01"))
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError("El presupuesto debe ser un número válido")

            cursor.execute(
                """
                INSERT INTO proyectos (propietario_id, titulo, descripcion, presupuesto, estado, fecha_publicacion)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, propietario_id, titulo
                """, 
                (propietario_id, titulo, descripcion, presupuesto_decimal, estado, fecha_publicacion)
            )

            proyecto_creado = cursor.fetchone()
            cursor.connection.commit()
            if proyecto_creado is None:
                return None

            return {
                "id": str(proyecto_creado[0]),
                "propietario_id": str(proyecto_creado[1]),
                "titulo": proyecto_creado[2],
            }

        except psycopg2.Error:
            cursor.connection.rollback()
            raise

        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def listar_proyectos(propietario_id: str | None = None, inversionista_id: str | None = None):
        cursor = Proyecto_controller.obtener_cursor()

        try:
            if propietario_id:
                cursor.execute(
                    """
                    SELECT id, propietario_id, titulo, descripcion, presupuesto, estado, fecha_publicacion, creado_en, actualizado_en, analisis_ai, COALESCE(solicitudes, 0) as solicitudes
                    FROM proyectos
                    WHERE propietario_id = %s
                    ORDER BY creado_en DESC
                    """,
                    (propietario_id,),
                )
            elif inversionista_id:
                cursor.execute(
                    """
                    SELECT
                        p.id, p.propietario_id, p.titulo, p.descripcion, p.presupuesto, p.estado,
                        p.fecha_publicacion, p.creado_en, p.actualizado_en, p.analisis_ai, COALESCE(p.solicitudes, 0) as solicitudes
                    FROM proyectos p
                    WHERE p.estado = 'activo'
                       OR EXISTS (
                           SELECT 1
                           FROM inversiones inv
                           JOIN inversionistas i ON i.id = inv.inversionista_id
                           WHERE inv.proyecto_id = p.id
                             AND i.usuario_id = %s
                       )
                    ORDER BY p.creado_en DESC
                    """,
                    (inversionista_id,),
                )
            else:
                # Para listas globales sin filtro, solo mostrar proyectos activos
                # Los proyectos inactivos permanecerán accesibles solo vía propietario_id
                # o si el inversionista ya forma parte del proyecto (vía inversiones)
                cursor.execute(
                    """
                    SELECT id, propietario_id, titulo, descripcion, presupuesto, estado, fecha_publicacion, creado_en, actualizado_en, analisis_ai, COALESCE(solicitudes, 0) as solicitudes
                    FROM proyectos
                    WHERE estado = 'activo'
                    ORDER BY creado_en DESC
                    """
                )

            filas = cursor.fetchall()
            proyectos = []
            for fila in filas:
                proyectos.append(
                    {
                        "id": str(fila[0]),
                        "propietario_id": str(fila[1]),
                        "titulo": fila[2],
                        "descripcion": fila[3],
                        "presupuesto": float(fila[4]) if fila[4] is not None else 0,
                        "estado": fila[5],
                        "fecha_publicacion": fila[6].isoformat() if fila[6] else None,
                        "creado_en": fila[7].isoformat() if fila[7] else None,
                        "actualizado_en": fila[8].isoformat() if fila[8] else None,
                        "analisis_ai": fila[9],
                        "solicitudes": int(fila[10]) if fila[10] is not None else 0,
                    }
                )

            return proyectos
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def obtener_proyecto(proyecto_id: str):
        cursor = Proyecto_controller.obtener_cursor()
        try:
            cursor.execute(
                """
                SELECT id, propietario_id, titulo, descripcion, presupuesto, estado, fecha_publicacion, creado_en, actualizado_en, analisis_ai, COALESCE(solicitudes, 0) as solicitudes
                FROM proyectos
                WHERE id = %s
                """,
                (proyecto_id,),
            )
            fila = cursor.fetchone()
            if not fila:
                return None
            return {
                "id": str(fila[0]),
                "propietario_id": str(fila[1]),
                "titulo": fila[2],
                "descripcion": fila[3],
                "presupuesto": float(fila[4]) if fila[4] is not None else 0,
                "estado": fila[5],
                "fecha_publicacion": fila[6].isoformat() if fila[6] else None,
                "creado_en": fila[7].isoformat() if fila[7] else None,
                "actualizado_en": fila[8].isoformat() if fila[8] else None,
                "analisis_ai": fila[9],
                "solicitudes": int(fila[10]) if fila[10] is not None else 0,
            }
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def actualizar_analisis_ai(proyecto_id: str, analisis: str):
        cursor = Proyecto_controller.obtener_cursor()
        try:
            cursor.execute(
                """
                UPDATE proyectos
                SET analisis_ai = %s, actualizado_en = NOW()
                WHERE id = %s
                """,
                (analisis, proyecto_id),
            )
            cursor.connection.commit()
            return True
        except Exception as e:
            print(f"Error al actualizar analisis_ai: {e}")
            cursor.connection.rollback()
            return False
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def actualizar_proyecto(proyecto_id: str, titulo: str = None, descripcion: str = None, presupuesto: float = None, estado: str = None):
        cursor = Proyecto_controller.obtener_cursor()
        try:
            campos = []
            valores = []
            if titulo is not None:
                campos.append("titulo = %s")
                valores.append(titulo)
            if descripcion is not None:
                campos.append("descripcion = %s")
                valores.append(descripcion)
            if presupuesto is not None:
                campos.append("presupuesto = %s")
                valores.append(presupuesto)
            if estado is not None:
                campos.append("estado = %s")
                valores.append(estado)
            
            if not campos:
                return False
            
            valores.append(proyecto_id)
            sql = f"UPDATE proyectos SET {', '.join(campos)}, actualizado_en = NOW() WHERE id = %s"
            
            cursor.execute(sql, tuple(valores))
            cursor.connection.commit()
            return True
        except Exception as e:
            print(f"Error al actualizar proyecto: {e}")
            cursor.connection.rollback()
            return False
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
        return cursor

    @staticmethod
    def obtener_analiticas_propietario(propietario_id: str, meses_atras: int = 3):
        """
        Retorna métricas agregadas para un propietario:
        - totales: proyectos, activos, inactivos, presupuesto_total
        - solicitudes_totales
        - inversiones_totales (cantidad y monto)
        - estado de solicitudes
        - distribución por proyecto
        - series mensuales para solicitudes e inversiones (últimos `meses_atras` meses)
        """
        cursor = Proyecto_controller.obtener_cursor()
        try:
            # Totales proyectos
            cursor.execute(
                """
                SELECT
                    COUNT(*)::int AS total_proyectos,
                    SUM(CASE WHEN estado = 'activo' THEN 1 ELSE 0 END)::int AS proyectos_activos,
                    SUM(CASE WHEN estado = 'inactivo' THEN 1 ELSE 0 END)::int AS proyectos_inactivos,
                    COALESCE(SUM(presupuesto), 0)::numeric AS presupuesto_total
                FROM proyectos
                WHERE propietario_id = %s
                """,
                (propietario_id,)
            )
            tot = cursor.fetchone()

            # Solicitudes totales para los proyectos del propietario
            cursor.execute(
                """
                SELECT COUNT(*)::int FROM solicitudes_inversion si
                WHERE si.proyecto_id IN (SELECT id FROM proyectos WHERE propietario_id = %s)
                """,
                (propietario_id,)
            )
            solicitudes_totales = cursor.fetchone()[0]

            # Inversiones totales (cantidad y monto)
            cursor.execute(
                """
                SELECT COUNT(*)::int, COALESCE(SUM(monto), 0)::numeric
                FROM inversiones inv
                WHERE inv.proyecto_id IN (SELECT id FROM proyectos WHERE propietario_id = %s)
                """,
                (propietario_id,)
            )
            inversiones_info = cursor.fetchone()

            # Estado de solicitudes
            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN estado = 'pendiente' THEN 1 ELSE 0 END), 0)::int AS pendientes,
                    COALESCE(SUM(CASE WHEN estado = 'aceptada' THEN 1 ELSE 0 END), 0)::int AS aceptadas,
                    COALESCE(SUM(CASE WHEN estado = 'rechazada' THEN 1 ELSE 0 END), 0)::int AS rechazadas,
                    COALESCE(SUM(CASE WHEN estado = 'retirada' THEN 1 ELSE 0 END), 0)::int AS retiradas
                FROM solicitudes_inversion
                WHERE proyecto_id IN (SELECT id FROM proyectos WHERE propietario_id = %s)
                """,
                (propietario_id,)
            )
            solicitudes_estado = cursor.fetchone()

            # Top proyectos por solicitudes
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.titulo,
                    p.estado,
                    p.presupuesto,
                    COALESCE(COUNT(si.id), 0)::int AS solicitudes
                FROM proyectos p
                LEFT JOIN solicitudes_inversion si ON si.proyecto_id = p.id
                WHERE p.propietario_id = %s
                GROUP BY p.id, p.titulo, p.estado, p.presupuesto, p.creado_en
                ORDER BY solicitudes DESC, p.creado_en DESC
                LIMIT 5
                """,
                (propietario_id,)
            )
            top_solicitudes = cursor.fetchall()

            # Top proyectos por monto invertido
            cursor.execute(
                """
                SELECT
                    p.id,
                    p.titulo,
                    p.estado,
                    p.presupuesto,
                    COALESCE(COUNT(inv.id), 0)::int AS inversiones,
                    COALESCE(SUM(inv.monto), 0)::numeric AS monto_total
                FROM proyectos p
                LEFT JOIN inversiones inv ON inv.proyecto_id = p.id
                WHERE p.propietario_id = %s
                GROUP BY p.id, p.titulo, p.estado, p.presupuesto, p.creado_en
                ORDER BY monto_total DESC, inversiones DESC, p.creado_en DESC
                LIMIT 5
                """,
                (propietario_id,)
            )
            top_inversiones = cursor.fetchall()

            # Series mensuales: últimos N meses (incluye mes actual)
            cursor.execute(
                """
                SELECT to_char(date_trunc('month', t.mes), 'YYYY-MM') AS ym,
                       EXTRACT(YEAR FROM t.mes)::int AS yr,
                       EXTRACT(MONTH FROM t.mes)::int AS mo
                FROM (
                  SELECT (date_trunc('month', NOW()) - (interval '1 month' * generate_series(0, %s-1))) AS mes
                ) t
                ORDER BY t.mes ASC
                """,
                (meses_atras,)
            )
            meses_rows = cursor.fetchall()
            meses_keys = [r[0] for r in meses_rows]

            # Solicitudes por mes
            cursor.execute(
                f"""
                SELECT to_char(date_trunc('month', si.creado_en), 'YYYY-MM') AS ym, COUNT(*)::int AS cnt
                FROM solicitudes_inversion si
                WHERE si.proyecto_id IN (SELECT id FROM proyectos WHERE propietario_id = %s)
                  AND date_trunc('month', si.creado_en) >= date_trunc('month', NOW() - interval '%s month')
                GROUP BY ym
                """,
                (propietario_id, meses_atras - 1)
            )
            filas_solic = cursor.fetchall()
            mapa_solic = {r[0]: int(r[1]) for r in filas_solic}

            # Inversiones por mes (monto)
            cursor.execute(
                f"""
                SELECT to_char(date_trunc('month', inv.creado_en), 'YYYY-MM') AS ym, COALESCE(SUM(inv.monto),0)::numeric AS suma
                FROM inversiones inv
                WHERE inv.proyecto_id IN (SELECT id FROM proyectos WHERE propietario_id = %s)
                  AND date_trunc('month', inv.creado_en) >= date_trunc('month', NOW() - interval '%s month')
                GROUP BY ym
                """,
                (propietario_id, meses_atras - 1)
            )
            filas_inv = cursor.fetchall()
            mapa_inv = {r[0]: float(r[1]) for r in filas_inv}

            # Construir series ordenadas
            series = []
            for key in meses_keys:
                series.append({
                    "mes": key,
                    "solicitudes": int(mapa_solic.get(key, 0)),
                    "inversiones_monto": float(mapa_inv.get(key, 0.0)),
                })

            resultado = {
                "total_proyectos": int(tot[0] or 0),
                "proyectos_activos": int(tot[1] or 0),
                "proyectos_inactivos": int(tot[2] or 0),
                "presupuesto_total": float(tot[3]) if tot[3] is not None else 0.0,
                "solicitudes_totales": int(solicitudes_totales or 0),
                "inversiones_totales": int(inversiones_info[0] or 0),
                "inversiones_monto_total": float(inversiones_info[1]) if inversiones_info[1] is not None else 0.0,
                "solicitudes_por_estado": {
                    "pendientes": int(solicitudes_estado[0] or 0),
                    "aceptadas": int(solicitudes_estado[1] or 0),
                    "rechazadas": int(solicitudes_estado[2] or 0),
                    "retiradas": int(solicitudes_estado[3] or 0),
                },
                "top_proyectos_solicitudes": [
                    {
                        "id": str(row[0]),
                        "titulo": row[1],
                        "estado": row[2],
                        "presupuesto": float(row[3]) if row[3] is not None else 0.0,
                        "solicitudes": int(row[4] or 0),
                    }
                    for row in top_solicitudes
                ],
                "top_proyectos_inversiones": [
                    {
                        "id": str(row[0]),
                        "titulo": row[1],
                        "estado": row[2],
                        "presupuesto": float(row[3]) if row[3] is not None else 0.0,
                        "inversiones": int(row[4] or 0),
                        "monto_total": float(row[5]) if row[5] is not None else 0.0,
                    }
                    for row in top_inversiones
                ],
                "series": series,
            }

            return resultado
        finally:
            cursor.close()
            cursor.connection.close()

    @staticmethod
    def obtener_proyeccion_proyecto(proyecto_id: str, meses_historial: int = 6, meses_prediccion: int = 3, include_mensajes: bool = False):
        """
        Calcula una proyección simple para un proyecto usando el historial
        de solicitudes e inversiones. Retorna series históricas por mes y
        predicciones para los siguientes meses usando regresión lineal simple.
        """
        cursor = Proyecto_controller.obtener_cursor()
        try:
            # Construir lista de meses históricos (incluye mes actual)
            cursor.execute(
                """
                SELECT to_char(date_trunc('month', t.mes), 'YYYY-MM') AS ym,
                       EXTRACT(YEAR FROM t.mes)::int AS yr,
                       EXTRACT(MONTH FROM t.mes)::int AS mo
                FROM (
                  SELECT (date_trunc('month', NOW()) - (interval '1 month' * generate_series(%s-1, 0, -1))) AS mes
                ) t
                ORDER BY t.mes ASC
                """,
                (meses_historial,)
            )
            meses_rows = cursor.fetchall()
            meses_keys = [r[0] for r in meses_rows]

            # Solicitudes por mes
            cursor.execute(
                f"""
                SELECT to_char(date_trunc('month', si.creado_en), 'YYYY-MM') AS ym, COUNT(*)::int AS cnt
                FROM solicitudes_inversion si
                WHERE si.proyecto_id = %s
                  AND date_trunc('month', si.creado_en) >= date_trunc('month', NOW() - interval '%s month')
                GROUP BY ym
                """,
                (proyecto_id, meses_historial - 1)
            )
            filas_solic = cursor.fetchall()
            mapa_solic = {r[0]: int(r[1]) for r in filas_solic}

            # Inversiones por mes (monto)
            cursor.execute(
                f"""
                SELECT to_char(date_trunc('month', inv.creado_en), 'YYYY-MM') AS ym, COALESCE(SUM(inv.monto),0)::numeric AS suma
                FROM inversiones inv
                WHERE inv.proyecto_id = %s
                  AND date_trunc('month', inv.creado_en) >= date_trunc('month', NOW() - interval '%s month')
                GROUP BY ym
                """,
                (proyecto_id, meses_historial - 1)
            )
            filas_inv = cursor.fetchall()
            mapa_inv = {r[0]: float(r[1]) for r in filas_inv}

            # Construir series históricas
            historico = []
            for key in meses_keys:
                historico.append({
                    "mes": key,
                    "solicitudes": int(mapa_solic.get(key, 0)),
                    "inversiones_monto": float(mapa_inv.get(key, 0.0)),
                })

            # Función simple de regresión lineal (x: 0..n-1)
            def linear_predict(values, steps):
                n = len(values)
                if n == 0:
                    return [0] * steps
                if n == 1:
                    return [values[0]] * steps
                xs = list(range(n))
                ys = values
                x_mean = sum(xs) / n
                y_mean = sum(ys) / n
                num = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
                den = sum((xs[i] - x_mean) ** 2 for i in range(n))
                slope = (num / den) if den != 0 else 0
                intercept = y_mean - slope * x_mean
                preds = []
                for i in range(n, n + steps):
                    preds.append(max(0, slope * i + intercept))
                return preds

            solicitudes_hist = [item["solicitudes"] for item in historico]
            inversiones_hist = [item["inversiones_monto"] for item in historico]

            solicitudes_pred = linear_predict(solicitudes_hist, meses_prediccion)
            inversiones_pred = linear_predict(inversiones_hist, meses_prediccion)

            # Construir meses proyectados (YYYY-MM)
            proyectados = []
            from datetime import datetime
            from dateutil.relativedelta import relativedelta
            # Mes siguiente al último histórico
            if meses_keys:
                last_parts = meses_keys[-1].split('-')
                last_dt = datetime(int(last_parts[0]), int(last_parts[1]) + 1, 1)
            else:
                last_dt = datetime.now()

            for i in range(meses_prediccion):
                mes_dt = last_dt + relativedelta(months=i)
                key = f"{mes_dt.year:04d}-{mes_dt.month:02d}"
                proyectados.append({
                    "mes": key,
                    "solicitudes": int(round(solicitudes_pred[i])) if i < len(solicitudes_pred) else 0,
                    "inversiones_monto": float(round(inversiones_pred[i], 2)) if i < len(inversiones_pred) else 0.0,
                })

            resultado = {
                "historico": historico,
                "proyectado": proyectados,
                "metrica": {
                    "ultima_solicitudes": solicitudes_hist[-1] if solicitudes_hist else 0,
                    "ultima_inversiones_monto": inversiones_hist[-1] if inversiones_hist else 0.0,
                }
            }

            # Añadir una serie combinada (histórico + proyectado) y marcar los puntos proyectados
            try:
                combined = []
                for item in historico:
                    combined.append({
                        "mes": item.get("mes"),
                        "solicitudes": int(item.get("solicitudes", 0)),
                        "inversiones_monto": float(item.get("inversiones_monto", 0.0)),
                        "proyectado": False,
                    })
                for item in proyectados:
                    combined.append({
                        "mes": item.get("mes"),
                        "solicitudes": int(item.get("solicitudes", 0)),
                        "inversiones_monto": float(item.get("inversiones_monto", 0.0)),
                        "proyectado": True,
                    })

                resultado["series"] = combined
            except Exception:
                resultado["series"] = [*historico, *proyectados]

            # Opcional: incluir métricas de mensajería provenientes de Firestore
            if include_mensajes:
                try:
                    from ..core.firebase_conection import firestore_db
                    from dateutil.relativedelta import relativedelta
                    from datetime import datetime

                    # Obtener propietario (user id) del proyecto
                    cursor.execute("SELECT propietario_id FROM proyectos WHERE id = %s", (proyecto_id,))
                    row_prop = cursor.fetchone()
                    propietario_id = str(row_prop[0]) if row_prop and row_prop[0] is not None else None

                    # Obtener usuario_id de inversionistas que hicieron solicitudes
                    cursor.execute(
                        """
                        SELECT DISTINCT i.usuario_id
                        FROM solicitudes_inversion si
                        JOIN inversionistas i ON si.inversionista_id = i.id
                        WHERE si.proyecto_id = %s
                        """,
                        (proyecto_id,)
                    )
                    inv_rows = cursor.fetchall()
                    inversionista_user_ids = [str(r[0]) for r in inv_rows if r and r[0]]

                    # Preparar ventana temporal
                    now = datetime.utcnow()
                    start_dt = now - relativedelta(months=meses_historial)

                    total_msgs = 0
                    msgs_by_month = {}
                    # response times: owner response (owner->investor) and investor response
                    owner_response_deltas = []
                    investor_response_deltas = []

                    if isinstance(firestore_db, object) and getattr(firestore_db, "collection", None):
                        participants = [pid for pid in inversionista_user_ids]
                        # incluir chats entre propietario y cada inversionista
                        for inv_user in participants:
                            if not propietario_id or not inv_user:
                                continue
                            # construir chat id igual que cliente: ordenar y unir con '__'
                            pair = sorted([str(propietario_id), str(inv_user)])
                            chat_id = f"{pair[0]}__{pair[1]}"

                            try:
                                msgs_ref = firestore_db.collection("chats").document(chat_id).collection("messages")
                                query = msgs_ref.where("createdAt", ">=", start_dt).order_by("createdAt")
                                docs = list(query.stream())

                                last_msg = None
                                for d in docs:
                                    data = d.to_dict()
                                    total_msgs += 1
                                    # agrupar por mes
                                    created = data.get("createdAt")
                                    if hasattr(created, "isoformat"):
                                        ym = created.strftime("%Y-%m")
                                    else:
                                        try:
                                            # fallback si viene como string
                                            from dateutil import parser as dateparser
                                            parsed = dateparser.parse(str(created))
                                            ym = parsed.strftime("%Y-%m")
                                        except Exception:
                                            ym = "unknown"

                                    msgs_by_month[ym] = msgs_by_month.get(ym, 0) + 1

                                    # calcular tiempos de respuesta
                                    sender = str(data.get("senderId") or data.get("sender_id") or "")
                                    ts = None
                                    if hasattr(created, "timestamp"):
                                        # Firestore Timestamp
                                        try:
                                            ts = created.to_datetime()
                                        except Exception:
                                            ts = created
                                    else:
                                        ts = created

                                    if last_msg and last_msg.get("sender") != sender and ts:
                                        prev_ts = last_msg.get("ts")
                                        if prev_ts and isinstance(prev_ts, datetime) and isinstance(ts, datetime):
                                            delta = (ts - prev_ts).total_seconds()
                                            # quien respondió es 'sender'
                                            if str(sender) == str(propietario_id):
                                                # owner responded to investor
                                                owner_response_deltas.append(delta)
                                            else:
                                                investor_response_deltas.append(delta)

                                    last_msg = {"sender": sender, "ts": ts}

                            except Exception:
                                # si falla una consulta Firestore, seguimos con lo demás
                                continue

                    # Calcular mediana y percentiles de tiempos de respuesta
                    def _percentile(sorted_list, p):
                        # p en [0,100]
                        if not sorted_list:
                            return None
                        n = len(sorted_list)
                        if n == 1:
                            return float(sorted_list[0])
                        # posición real (0-indexed)
                        k = (n - 1) * (p / 100.0)
                        f = int(k)
                        c = f + 1
                        if c >= n:
                            return float(sorted_list[-1])
                        d0 = sorted_list[f] * (c - k)
                        d1 = sorted_list[c] * (k - f)
                        return float(d0 + d1)

                    owner_sorted = sorted(owner_response_deltas)
                    inv_sorted = sorted(investor_response_deltas)

                    resultado["mensajes"] = {
                        "total": total_msgs,
                        "por_mes": msgs_by_month,
                        "owner_response": {
                            "count": len(owner_sorted),
                            "median_seconds": _percentile(owner_sorted, 50),
                            "p75_seconds": _percentile(owner_sorted, 75),
                            "p90_seconds": _percentile(owner_sorted, 90),
                        },
                        "investor_response": {
                            "count": len(inv_sorted),
                            "median_seconds": _percentile(inv_sorted, 50),
                            "p75_seconds": _percentile(inv_sorted, 75),
                            "p90_seconds": _percentile(inv_sorted, 90),
                        },
                    }
                except Exception as e:
                    # No queremos que errores en mensajería rompan la respuesta
                    resultado["mensajes"] = {"error": str(e)}

            return resultado
        finally:
            cursor.close()
            cursor.connection.close()
