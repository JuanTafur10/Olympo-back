import os
import json
from groq import Groq
from ..controller.proyecto_controller import Proyecto_controller

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

class IAAsistente:
    @staticmethod
    def mensaje_chatbot(mensaje_usuario: str, usuario_id: str = None):
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return "Error: No se encontró la clave de Groq."

            client = Groq(api_key=api_key)

            # Obtener proyectos del usuario si se proporciona usuario_id
            contexto_proyectos = ""
            if usuario_id:
                try:
                    proyectos = Proyecto_controller.listar_proyectos(propietario_id=usuario_id)
                    if proyectos:
                        contexto_proyectos = "\n\nInformación de los proyectos del usuario:\n"
                        for p in proyectos:
                            contexto_proyectos += f"- Título: {p['titulo']}\n  Descripción: {p['descripcion']}\n  Presupuesto: {p['presupuesto']}\n  Estado: {p['estado']}\n"
                        contexto_proyectos += "\nUsa esta información para dar sugerencias personalizadas, consejos de mejora o estrategias de inversión si el usuario pregunta sobre sus proyectos o cómo mejorar su emprendimiento."
                except Exception as e:
                    print(f"Error al obtener proyectos para el chatbot: {e}")

            system_instruction = (
                "Eres el asistente virtual de Olympo y tu nombre sera Atenea. Ayudas a los usuarios de la plataforma a resolver dudas sobre sus proyectos, ideas de negocio, perfiles de emprendedor o inversionista, comunicación dentro de la app y uso general del producto. "
                "Responde siempre en español, con tono claro, amable y profesional."
                f"{contexto_proyectos}"
            )

            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": mensaje_usuario}
                ],
                temperature=1,
                max_completion_tokens=1024,
                top_p=1,
                stream=False
            )

            return completion.choices[0].message.content
        
        except Exception as e:
            return f"Error al conectar con Groq: {e}"

    @staticmethod
    def optimizar_descripcion(titulo: str, descripcion_actual: str):
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return "Error: No se encontró la clave de Groq."

            client = Groq(api_key=api_key)

            system_instruction = (
                "Eres un Copywriter experto en Startups y Pitch Decks. "
                "Tu objetivo es tomar la descripción de un proyecto de emprendimiento y reescribirla para que sea mucho más atractiva, profesional y convincente para un inversionista. "
                "Debes mantener la esencia del proyecto pero usar un lenguaje que resalte el valor, la innovación y el potencial de mercado. "
                "Responde únicamente con el nuevo texto de la descripción, en español, sin comentarios adicionales ni introducciones."
                "Evita usar el doble ** para la negrilla"
            )

            prompt_usuario = (
                f"Proyecto: {titulo}\n"
                f"Descripción actual: {descripcion_actual}\n\n"
                "Por favor, optimiza esta descripción para que sea irresistible para inversionistas."
            )

            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt_usuario}
                ],
                temperature=0.8,
                max_completion_tokens=1000,
                top_p=1,
                stream=False
            )

            return completion.choices[0].message.content
        
        except Exception as e:
            return f"Error al optimizar descripción: {e}"

    @staticmethod
    def score_bot(proyecto_id: str):
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return "Error: No se encontró la clave de Groq."

            # Obtener datos del proyecto específico
            proyecto = Proyecto_controller.obtener_proyecto(proyecto_id)
            if not proyecto:
                return "Error: Proyecto no encontrado."

            client = Groq(api_key=api_key)

            system_instruction = (
                "Eres un Analista de Inversiones Senior con años de experiencia evaluando startups y proyectos de emprendimiento. "
                "Tu objetivo es realizar un 'Scoring' o evaluación técnica del proyecto que se te presenta. "
                "Debes evaluar los siguientes criterios del 1 al 10:\n"
                "1. Viabilidad del Mercado\n"
                "2. Escalabilidad\n"
                "3. Realismo del Presupuesto\n"
                "4. Claridad de la Propuesta\n\n"
                "Responde siempre en español con un tono profesional, crítico pero constructivo. "
                "Estructura tu respuesta con un resumen ejecutivo, el desglose de puntajes y una recomendación final para un potencial inversionista."
            )

            prompt_usuario = (
                f"Por favor, evalúa el siguiente proyecto:\n\n"
                f"Título: {proyecto['titulo']}\n"
                f"Descripción: {proyecto['descripcion']}\n"
                f"Presupuesto Solicitado: ${proyecto['presupuesto']}\n"
                f"Estado Actual: {proyecto['estado']}\n\n"
                "Dáme un análisis detallado y los puntajes correspondientes."
            )

            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt_usuario}
                ],
                temperature=0.7,  # Un poco más bajo para ser más consistente
                max_completion_tokens=1500,
                top_p=1,
                stream=False
            )

            return completion.choices[0].message.content
        
        except Exception as e:
            return f"Error en el proceso de scoring: {e}"

    @staticmethod
    def detectar_riesgos_emergentes_ares(proyecto_id: str):
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return {"error": "No se encontró la clave de Groq."}

            proyecto = Proyecto_controller.obtener_proyecto(proyecto_id)
            if not proyecto:
                return {"error": "Proyecto no encontrado."}

            client = Groq(api_key=api_key)

            def _nivel_riesgo(probabilidad: int, impacto: int) -> str:
                score = probabilidad * impacto
                if score >= 12:
                    return "alto"
                if score >= 6:
                    return "medio"
                return "bajo"

            def _ajustar_a_nivel(riesgo: dict, nivel_objetivo: str) -> dict:
                plantillas = {
                    "alto": (4, 4),
                    "medio": (3, 3),
                    "bajo": (1, 3),
                }
                prob, imp = plantillas.get(nivel_objetivo, (3, 3))
                r = dict(riesgo)
                r["probabilidad"] = prob
                r["impacto"] = imp
                return r

            def _fabricar_riesgo(nivel_objetivo: str, indice: int) -> dict:
                plantillas = {
                    "alto": (4, 4),
                    "medio": (3, 3),
                    "bajo": (1, 3),
                }
                prob, imp = plantillas.get(nivel_objetivo, (3, 3))
                return {
                    "categoria": "Detectado por IA",
                    "nombre": f"Riesgo {nivel_objetivo.capitalize()} #{indice}",
                    "descripcion": "Riesgo identificado por IA para este proyecto.",
                    "probabilidad": prob,
                    "impacto": imp,
                    "tratamiento": "Definir plan de mitigación específico.",
                }

            def _forzar_distribucion_10(riesgos: list[dict]) -> list[dict]:
                objetivos = {"alto": 4, "medio": 3, "bajo": 3}
                niveles = ["alto", "medio", "bajo"]

                # Agrupar por nivel real
                grupos = {"alto": [], "medio": [], "bajo": []}
                for r in riesgos:
                    nivel = _nivel_riesgo(int(r.get("probabilidad", 3)), int(r.get("impacto", 3)))
                    grupos[nivel].append(r)

                seleccion = []
                restantes = []

                for nivel in niveles:
                    cupo = objetivos[nivel]
                    directos = grupos[nivel][:cupo]
                    seleccion.extend(directos)
                    faltan = cupo - len(directos)
                    if faltan > 0:
                        # Guardar faltantes para completarlos luego
                        restantes.extend([nivel] * faltan)

                # Candidatos sobrantes de cualquier nivel
                sobrantes = []
                for nivel in niveles:
                    sobrantes.extend(grupos[nivel][objetivos[nivel]:])

                # Reusar sobrantes ajustando prob/impact para cubrir niveles faltantes
                for nivel_faltante in list(restantes):
                    if not sobrantes:
                        break
                    base = sobrantes.pop(0)
                    seleccion.append(_ajustar_a_nivel(base, nivel_faltante))
                    restantes.remove(nivel_faltante)

                # Si aún faltan, fabricar riesgos de respaldo
                contador = 1
                for nivel_faltante in restantes:
                    seleccion.append(_fabricar_riesgo(nivel_faltante, contador))
                    contador += 1

                return seleccion[:10]

            system_instruction = (
                "Eres 'Ares', un Analista de Riesgos experto en Startups. "
                "Debes detectar riesgos específicos del proyecto, sin depender de un catálogo predefinido. "
                "Responde SOLO un JSON válido con esta estructura exacta: "
                "{\"riesgos_detectados\":[{\"categoria\":\"...\",\"nombre\":\"...\",\"descripcion\":\"...\",\"probabilidad\":3,\"impacto\":4,\"tratamiento\":\"...\"}]}. "
                "Debes retornar exactamente 10 riesgos: 4 de nivel alto, 3 de nivel medio y 3 de nivel bajo. "
                "No repitas riesgos ni nombres. "
                "Probabilidad e impacto deben ser enteros de 1 a 5."
            )

            prompt_usuario = (
                "Genera exactamente 10 riesgos para este proyecto con esta distribución: 4 altos, 3 medios, 3 bajos.\n"
                "Recuerda: nivel alto score >= 12, nivel medio score 6-11, nivel bajo score <= 5.\n\n"
                f"Proyecto: {proyecto.get('titulo')}\n"
                f"Descripción: {proyecto.get('descripcion')}\n"
                f"Presupuesto: {proyecto.get('presupuesto')}\n"
                f"Estado: {proyecto.get('estado')}\n"
            )

            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt_usuario},
                ],
                temperature=0.35,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
                response_format={"type": "json_object"},
            )

            respuesta_texto = completion.choices[0].message.content
            try:
                datos_json = json.loads(respuesta_texto)
            except json.JSONDecodeError:
                return {"error": "Respuesta inválida del modelo", "raw": respuesta_texto}

            riesgos = datos_json.get("riesgos_detectados") if isinstance(datos_json, dict) else None
            if not isinstance(riesgos, list):
                riesgos = []

            riesgos_limpios = []
            nombres_vistos = set()
            for item in riesgos:
                if not isinstance(item, dict):
                    continue

                nombre = str(item.get("nombre") or "").strip()
                categoria = str(item.get("categoria") or "General").strip()
                descripcion = str(item.get("descripcion") or "").strip()
                tratamiento = str(item.get("tratamiento") or "Definir plan de mitigación específico.").strip()
                try:
                    probabilidad = int(item.get("probabilidad", 3))
                except Exception:
                    probabilidad = 3
                try:
                    impacto = int(item.get("impacto", 3))
                except Exception:
                    impacto = 3

                probabilidad = max(1, min(5, probabilidad))
                impacto = max(1, min(5, impacto))

                if not nombre:
                    continue

                nombre_key = nombre.lower()
                if nombre_key in nombres_vistos:
                    continue
                nombres_vistos.add(nombre_key)

                riesgos_limpios.append(
                    {
                        "categoria": categoria or "General",
                        "nombre": nombre,
                        "descripcion": descripcion or "Riesgo identificado por IA para este proyecto.",
                        "probabilidad": probabilidad,
                        "impacto": impacto,
                        "tratamiento": tratamiento,
                    }
                )

            riesgos_finales = _forzar_distribucion_10(riesgos_limpios)
            return {"riesgos_detectados": riesgos_finales}
        except Exception as e:
            return {"error": f"Error en la detección de riesgos emergentes: {e}"}