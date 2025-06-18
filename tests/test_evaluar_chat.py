import json
from pathlib import Path
import sys
import types

# Añadir carpeta src al path
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import evaluar_chat


def test_evaluar_entregas(monkeypatch, tmp_path):
    # Datos de ejemplo
    datos = [
        {"nombre": "A", "resolucion": "print(1)", "tarea": "t"},
        {"nombre": "B", "resolucion": "no realiza", "tarea": "t"},
    ]

    # Dummy result
    def dummy_eval(client, nombre, resolucion, tarea):
        return {"calificacion": {"total": 5, "detalle": [2, 1, 1, 1]}, "comentarios": "ok"}

    monkeypatch.setattr(evaluar_chat, "_load_client", lambda: "client")
    monkeypatch.setattr(evaluar_chat, "evaluar_con_chat", lambda client, nombre, resolucion, tarea: dummy_eval(client, nombre, resolucion, tarea))

    res = evaluar_chat.evaluar_entregas(datos, client="client")
    assert res[0]["calificacion"]["total"] == 5
    assert res[1]["calificacion"]["total"] == 0

    # Test archivo
    input_file = tmp_path / "in.json"
    output_file = tmp_path / "out.json"
    input_file.write_text(json.dumps(datos))

    evaluar_chat.evaluate_file(input_file, output_file)
    saved = json.loads(output_file.read_text())
    assert saved[0]["calificacion"]["total"] == 5
