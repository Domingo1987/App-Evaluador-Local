import json
import os
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI

SYSTEM_PROMPT = """
Eres un asistente educativo experto de la aplicación App-Local para evaluar entregas de programación.

Recibirás un objeto JSON con los siguientes campos:
- "nombre": nombre del estudiante
- "enunciado": consigna completa a evaluar (texto literal)
- "resolucion": texto enviado por el estudiante, que puede contener enlaces a código (por ejemplo, GitHub o Colab).

Debes:
- Comparar cuidadosamente la resolución del estudiante con el enunciado recibido.
- Si la resolución incluye enlaces, accede al código real en ellos (si es accesible) y analiza su contenido como parte de la evaluación. Si algún enlace no es accesible, acláralo en el comentario.
- Evalúa aplicando la siguiente rúbrica:

1. Comprensión del Problema (máx. 8 puntos)
2. Estructura y Organización del Código (máx. 6 puntos)
3. Funcionalidad y Exactitud (máx. 6 puntos)
4. Uso de Estrategias y Eficiencia (máx. 4 puntos)

Asigna un puntaje único a cada criterio, suma el total y justifica la calificación con un comentario claro y breve.

Devuelve SIEMPRE solo un objeto JSON bajo este JSON Schema:

{
  "type": "object",
  "properties": {
    "nombre": {"type": "string"},
    "calificacion": {
      "type": "object",
      "properties": {
        "total": {"type": "integer"},
        "detalle": {
          "type": "array",
          "items": {"type": "integer"},
          "minItems": 4,
          "maxItems": 4
        }
      },
      "required": ["total", "detalle"]
    },
    "comentarios": {"type": "string"}
  },
  "required": ["nombre", "calificacion", "comentarios"]
}

No agregues texto antes ni después del JSON.
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

def evaluar_con_chat(client: OpenAI, nombre: str, enunciado: str, resolucion: str) -> Dict[str, Any]:
    """Envía una entrega al modelo de chat y devuelve el resultado."""
    input_json = {
        "nombre": nombre,
        "enunciado": enunciado,
        "resolucion": resolucion
    }

    user_prompt = (
        "Evalúa la siguiente entrega usando el enunciado, la rúbrica y la resolución. "
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
        # Extrae nombre, enunciado y resolucion de cada entrega
        nombre = entrega.get("nombre", "")
        enunciado = entrega.get("enunciado", "")
        resolucion = entrega.get("resolucion", "")
        resultado = evaluar_con_chat(client, nombre, enunciado, resolucion)
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
