import sys
import json
import os
from bs4 import BeautifulSoup

# USO: python App-api.py archivo_salida.json id_curso [estudiantes.json] [scrap.txt]
if len(sys.argv) < 3:
    print("Uso: python App-api.py archivo_salida.json id_curso [estudiantes.json] [scrap.txt]")
    sys.exit(1)

archivo_salida = sys.argv[1]
id_curso = int(sys.argv[2])
json_path = sys.argv[3] if len(sys.argv) > 3 else "estudiantes.json"
scrap_path = sys.argv[4] if len(sys.argv) > 4 else "scrap.txt"

def cargar_json(path):
    if not os.path.exists(path):
        print(f"No se encuentra el archivo {path}.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- Busca el curso por ID ---
def buscar_curso_por_id(cursos, id_curso):
    for curso in cursos:
        if curso.get("id") == id_curso:
            return curso
    return None

data = cargar_json(json_path)
if not isinstance(data, list):
    print("El archivo estudiantes.json debe contener una lista de cursos.")
    sys.exit(1)
curso = buscar_curso_por_id(data, id_curso)
if curso is None:
    print(f"No se encontró un curso con id={id_curso}.")
    sys.exit(1)
estudiantes = curso.get("estudiantes", [])
lista_nombres = [e["nombre_crea"] for e in estudiantes]

def scrap_schoology(path, lista_nombres):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    entregas = {}
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="discussion-card")
    for card in cards:
        nombre_tag = card.find("span", class_="comment-author")
        if not nombre_tag:
            continue
        nombre = nombre_tag.get_text(strip=True)
        for nombre_crea in lista_nombres:
            if nombre_crea.upper() == nombre.upper():
                cuerpo = card.find("div", class_="comment-body-wrapper")
                if cuerpo:
                    textos = [p.get_text(" ", strip=True) for p in cuerpo.find_all("p")]
                    links = [a["href"] for a in cuerpo.find_all("a", href=True)
                             if not a["href"].startswith(("/user/", "/comment/", "/discussion/", "/likes/", "/course/"))]
                    texto_entrega = " ".join(textos)
                else:
                    texto_entrega = ""
                    links = []
                # Adjuntos
                adjuntos = card.find_all("div", class_="attachments-link-summary")
                links_adjuntos = [adj.get_text(" ", strip=True) for adj in adjuntos]
                # Unir links y adjuntos
                all_links = list(dict.fromkeys(links + links_adjuntos))
                if all_links:
                    texto_entrega += ("\nAdjuntos:\n" if texto_entrega else "Adjuntos:\n") + "\n".join(all_links)
                entregas[nombre_crea] = texto_entrega.strip()
                break
    return entregas

entregas = scrap_schoology(scrap_path, lista_nombres)

evaluaciones = []
for i, estudiante in enumerate(estudiantes, 1):
    nombre_json = estudiante["nombre_crea"]
    if nombre_json in entregas:
        evaluacion = {
            "numero": i,
            "nombre": nombre_json,
            "resolucion": entregas[nombre_json],
            "calificacion": { "total": 0, "detalle": [0,0,0,0] },
            "comentarios": ""
        }
    else:
        evaluacion = {
            "numero": i,
            "nombre": nombre_json,
            "resolucion": "no realiza",
            "calificacion": { "total": 0, "detalle": [0,0,0,0] },
            "comentarios": ""
        }
    evaluaciones.append(evaluacion)

# --- Salida ---
# Si el curso tiene estudiantes: solo lista de evaluaciones.
# Si no hay estudiantes: contexto + evaluaciones vacía.
if estudiantes:
    resultado = evaluaciones
else:
    resultado = {
        "id": curso.get("id"),
        "slug": curso.get("slug", ""),
        "año": curso.get("año"),
        "curso": curso.get("curso"),
        "centro": curso.get("centro"),
        "evaluaciones": []
    }

# Obtiene el slug y construye la ruta destino
slug = curso.get("slug")
if not slug:
    print("Error: el curso seleccionado no tiene campo 'slug'.")
    sys.exit(1)

ruta_destino = os.path.join("../Evaluaciones", slug)
os.makedirs(ruta_destino, exist_ok=True)

ruta_archivo = os.path.join(ruta_destino, archivo_salida)

with open(ruta_archivo, "w", encoding="utf-8") as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print(f"¡JSON generado y guardado como {ruta_archivo}!")