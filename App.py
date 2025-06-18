import streamlit as st
import json
import os
from bs4 import BeautifulSoup

st.title("Panel de Evaluación - Scrap Schoology (multi-cursos)")

json_path = "estudiantes.json"
scrap_path = "scrap.txt"

@st.cache_data
def cargar_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

cursos = cargar_json(json_path)
if not cursos or not isinstance(cursos, list):
    st.error(f"No se encuentra o no es válido el archivo {json_path}.")
    st.stop()

# Selección de curso
opciones = [f"{c.get('id', '?')} - {c.get('curso', '?')} ({c.get('centro','')})" for c in cursos]
opcion = st.selectbox("Selecciona el curso:", opciones)
curso_idx = opciones.index(opcion)
curso = cursos[curso_idx]

st.info(f"Curso seleccionado: {curso.get('curso')} ({curso.get('id')})")
nombre_tarea = st.text_input("Nombre de la tarea:", "3_7_Arreglos")
nombre_archivo = st.text_input("Nombre de archivo de salida (sin .json):", "3_7_acti_res")

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

estudiantes = curso.get("estudiantes", [])
lista_nombres = [e["nombre_crea"] for e in estudiantes]

if estudiantes:
    st.success(f"Encontrados {len(estudiantes)} estudiantes.")
    st.table([{"Nombre": e["nombre"], "Nombre CREA": e["nombre_crea"]} for e in estudiantes])
else:
    st.warning("Este curso no tiene estudiantes cargados.")

entregas = scrap_schoology(scrap_path, lista_nombres)

if st.button("Generar y mostrar JSON de Evaluación"):
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

    st.subheader("JSON de Evaluación generado:")
    st.json(evaluaciones)

    nombre_final = nombre_archivo.strip() + ".json"
    json_str = json.dumps(evaluaciones, ensure_ascii=False, indent=2)

    # Guarda localmente el archivo
    with open(nombre_final, "w", encoding="utf-8") as f:
        f.write(json_str)

    # Botón de descarga
    st.download_button(
        label=f"Descargar {nombre_final}",
        data=json_str,
        file_name=nombre_final,
        mime="application/json"
    )
    st.success(f"¡JSON listo para descargar y guardado como {nombre_final}!")
