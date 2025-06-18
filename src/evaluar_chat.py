import json
import os
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI

SYSTEM_PROMPT = """Sos un asistente educativo de evaluación.
Tu tarea es analizar entregas de estudiantes de programación.
Antes de evaluar cualquier entrega, debés buscar la consigna original en el archivo de consignas correspondiente (por ejemplo, consignas_p1.json), usando el identificador o nombre de la tarea recibido en el JSON. Utilizá la consigna original como referencia principal para la evaluación.
Si la resolución incluye un enlace a código o notebook, evaluá tanto el texto de la entrega como el contenido de ese enlace (si está presente y es accesible). Si el enlace no se incluye o no es accesible, indicálo en el comentario.

Debes:
- Leer el objeto JSON recibido, que contiene los campos "nombre" (nombre del estudiante), "resolucion" (texto de la entrega), y "consigna" (identificador o nombre de la tarea).
- Buscar la consigna de referencia antes de realizar la evaluación.
- Evaluar la entrega aplicando cuidadosamente la siguiente rúbrica, asegurando que cada criterio esté alineado con lo solicitado en la consigna.

RÚBRICA:
1. Comprensión del Problema (máx. 8 puntos)
2. Estructura y Organización del Código (máx. 6 puntos)
3. Funcionalidad y Exactitud (máx. 6 puntos)
4. Uso de Estrategias y Eficiencia (máx. 4 puntos)

Asigna un puntaje para cada criterio (solo uno por criterio), suma el total y genera un comentario claro y específico para el estudiante, haciendo referencia a la consigna original y la resolución presentada.

Devuelve SIEMPRE el resultado en formato JSON, cumpliendo con el siguiente esquema (no agregues texto antes ni después del JSON):
{
  "nombre": "Nombre del estudiante",
  "calificacion": {
    "total": <suma de los puntajes>,
    "detalle": [<comprension>, <estructura>, <funcionalidad>, <estrategias>]
  },
  "comentarios": "Comentario para el estudiante."
}

Condiciones adicionales:
- Si la consigna no se puede identificar, avisálo en el comentario.
- Si hay enlaces no accesibles, especificálo.
- El comentario debe ser claro, breve y específico sobre la entrega.
"""


def _load_client() -> OpenAI:
    """Crea una instancia del cliente OpenAI a partir de la API key."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "No se encontró OPENAI_API_KEY. Agrégalo a .env o usa export."
        )
    return OpenAI(api_key=api_key)


def evaluar_con_chat(client: OpenAI, nombre: str, resolucion: str, tarea: str) -> Dict[str, Any]:
    """Envía una entrega al modelo de chat y devuelve el resultado."""
    input_json = {"nombre": nombre, "resolucion": resolucion, "consigna": tarea}

    user_prompt = (
        "Evalúa la siguiente entrega usando la consigna dada por clave, la rúbrica y la resolución. "
        "Devuelve solo el JSON requerido.\n\nDatos de la entrega:\n"
        f"{json.dumps(input_json, ensure_ascii=False, indent=2)}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
        temperature=0,
    )
    final_msg = response.choices[0].message.content.strip()

    clean_msg = final_msg
    if "```json" in clean_msg:
        clean_msg = clean_msg.split("```json")[1].split("```", 1)[0].strip()
    elif "```" in clean_msg:
        clean_msg = clean_msg.split("```", 1)[1].split("```", 1)[0].strip()

    resultado = json.loads(clean_msg)
    resultado.setdefault("calificacion", {"total": 0, "detalle": [0, 0, 0, 0]})
    resultado.setdefault("comentarios", "Evaluación completada")
    return resultado


def evaluar_entregas(evaluaciones: List[Dict[str, Any]], client: OpenAI | None = None) -> List[Dict[str, Any]]:
    """Evalúa una lista de entregas utilizando OpenAI."""
    if client is None:
        client = _load_client()

    for entrega in evaluaciones:
        if entrega.get("resolucion", "").strip().lower() == "no realiza":
            entrega.setdefault("calificacion", {"total": 0, "detalle": [0, 0, 0, 0]})
            entrega.setdefault("comentarios", "")
            continue
        tarea = entrega.get("tarea") or entrega.get("consigna") or "3_7_tarea1"
        resultado = evaluar_con_chat(client, entrega["nombre"], entrega["resolucion"], tarea)
        entrega["calificacion"] = resultado.get("calificacion", {"total": 0, "detalle": [0, 0, 0, 0]})
        entrega["comentarios"] = resultado.get("comentarios", "")
    return evaluaciones


def evaluate_file(archivo_entrada: str | Path, archivo_salida: str | Path) -> None:
    """Procesa un archivo de entregas y guarda las evaluaciones."""
    entrada = Path(archivo_entrada)
    salida = Path(archivo_salida)
    if not entrada.exists():
        raise FileNotFoundError(f"No se encontró el archivo de entrada: {entrada}")

    with entrada.open("r", encoding="utf-8") as f:
        evaluaciones = json.load(f)

    evaluar_entregas(evaluaciones)

    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", encoding="utf-8") as f:
        json.dump(evaluaciones, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        msg = "Uso: python evaluar_chat.py archivo_entrada.json archivo_salida.json"
        raise SystemExit(msg)

    evaluate_file(sys.argv[1], sys.argv[2])
