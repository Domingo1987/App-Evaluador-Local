import streamlit as st
import json
import os
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Evaluación Automática",
    page_icon="📝",
    layout="wide"
)

# Rutas principales
BASE_DIR = Path(__file__).parent.parent
DATA_INPUT = BASE_DIR / "data" / "input"
DATA_OUTPUT = BASE_DIR / "data" / "output"
CONFIG_DIR = BASE_DIR / "config"

# Crear directorios si no existen
DATA_INPUT.mkdir(parents=True, exist_ok=True)
DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def load_json(filepath):
    """Carga un archivo JSON de forma segura"""
    try:
        if Path(filepath).exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        st.error(f"Error cargando {filepath}: {e}")
        return None

def save_json(data, filepath):
    """Guarda datos en formato JSON"""
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Error guardando {filepath}: {e}")
        return False

def scrap_schoology(html_content, nombres_crea):
    """Extrae entregas del HTML de Schoology"""
    entregas = {}
    
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        cards = soup.find_all("div", class_="discussion-card")
        
        for card in cards:
            nombre_tag = card.find("span", class_="comment-author")
            if not nombre_tag:
                continue
                
            nombre = nombre_tag.get_text(strip=True)
            
            # Buscar coincidencia con los nombres CREA
            for nombre_crea in nombres_crea:
                if nombre_crea.upper() == nombre.upper():
                    # Extraer contenido
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
                    
                    # Unir todo
                    all_links = list(dict.fromkeys(links + links_adjuntos))
                    if all_links:
                        texto_entrega += ("\nAdjuntos:\n" if texto_entrega else "Adjuntos:\n") + "\n".join(all_links)
                    
                    entregas[nombre_crea] = texto_entrega.strip()
                    break
                    
    except Exception as e:
        st.error(f"Error procesando HTML: {e}")
        
    return entregas

def main():
    st.title("📝 Sistema de Evaluación Automática")
    st.markdown("---")
    
    # Sidebar con información
    with st.sidebar:
        st.header("🔧 Estado del Sistema")
        
        # Verificar archivos necesarios
        scrap_file = DATA_INPUT / "scrap.txt"
        estudiantes_file = CONFIG_DIR / "estudiantes.json"
        
        if scrap_file.exists():
            st.success("✅ HTML scrapeado disponible")
        else:
            st.warning("⚠️ No hay HTML scrapeado")
            
        if estudiantes_file.exists():
            st.success("✅ Base de estudiantes disponible")
        else:
            st.error("❌ Falta configuración de estudiantes")
    
    # PASO 1: Verificar HTML scrapeado
    st.header("1️⃣ Verificar HTML Scrapeado")
    
    scrap_path = DATA_INPUT / "scrap.txt"
    if scrap_path.exists():
        with open(scrap_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        st.success(f"✅ Archivo encontrado: {len(html_content)} caracteres")
        
        # Preview del contenido
        with st.expander("Ver preview del HTML"):
            st.text(html_content[:1000] + "..." if len(html_content) > 1000 else html_content)
    else:
        st.error("❌ No se encontró el archivo scrap.txt")
        st.info("📋 **Instrucciones:**\n1. Ve a la actividad en Schoology\n2. Selecciona todo el HTML (Ctrl+A)\n3. Copia (Ctrl+C)\n4. Pega el contenido en data/input/scrap.txt")
        st.stop()
    
    st.markdown("---")
    
    # PASO 2: Seleccionar curso
    st.header("2️⃣ Seleccionar Curso")
    
    estudiantes_data = load_json(CONFIG_DIR / "estudiantes.json")
    if not estudiantes_data:
        st.error("❌ No se pudo cargar la configuración de estudiantes")
        st.stop()
    
    # Filtrar solo cursos con estudiantes
    cursos_con_estudiantes = [curso for curso in estudiantes_data if curso.get("estudiantes")]
    
    if not cursos_con_estudiantes:
        st.warning("⚠️ No hay cursos con estudiantes registrados")
        st.stop()
    
    # Selectbox para curso
    opciones_curso = []
    for curso in cursos_con_estudiantes:
        num_estudiantes = len(curso.get("estudiantes", []))
        opcion = f"{curso.get('id', '?')} - {curso.get('curso', '?')} ({curso.get('centro', '')}) - {num_estudiantes} estudiantes"
        opciones_curso.append(opcion)
    
    curso_seleccionado_idx = st.selectbox(
        "Selecciona el curso:",
        range(len(opciones_curso)),
        format_func=lambda x: opciones_curso[x]
    )
    
    curso_seleccionado = cursos_con_estudiantes[curso_seleccionado_idx]
    
    # Información del curso
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("ID Curso", curso_seleccionado.get("id", "N/A"))
    with col2:
        st.metric("Estudiantes", len(curso_seleccionado.get("estudiantes", [])))
    with col3:
        st.metric("Centro", curso_seleccionado.get("centro", "N/A"))
    
    st.markdown("---")
    
    # PASO 3: Confirmar estudiantes
    st.header("3️⃣ Confirmar Estudiantes")
    
    estudiantes = curso_seleccionado.get("estudiantes", [])
    df_estudiantes = pd.DataFrame(estudiantes)
    
    st.dataframe(
        df_estudiantes,
        use_container_width=True,
        hide_index=True
    )
    
    confirmacion = st.checkbox("✅ Confirmo que la lista de estudiantes es correcta")
    
    if not confirmacion:
        st.warning("⚠️ Por favor confirma la lista de estudiantes antes de continuar")
        st.stop()
    
    st.markdown("---")
    
    # PASO 4: Seleccionar consigna
    st.header("4️⃣ Seleccionar Consigna")
    
    # Determinar archivo de consignas basado en el curso
    curso_slug = curso_seleccionado.get("slug", "")
    
    # Mapeo de slugs a archivos de consignas
    if "programacion1" in curso_slug.lower():
        consignas_file = CONFIG_DIR / "consignas_p1.json"
    elif "programacion2" in curso_slug.lower():
        consignas_file = CONFIG_DIR / "consignas_p2.json"
    else:
        consignas_file = CONFIG_DIR / "consignas_p1.json"  # Default
    
    consignas_data = load_json(consignas_file)
    if not consignas_data:
        st.error(f"❌ No se pudo cargar {consignas_file}")
        st.stop()
    
    # Selectbox para consigna
    consignas_keys = list(consignas_data.keys())
    consigna_seleccionada_key = st.selectbox(
        "Selecciona la tarea/consigna:",
        consignas_keys
    )
    
    # Preview de la consigna
    with st.expander("Ver consigna completa"):
        st.text_area(
            "Descripción:",
            consignas_data[consigna_seleccionada_key],
            height=200,
            disabled=True
        )
    
    st.markdown("---")
    
    # PASO 5: Procesar entregas
    st.header("5️⃣ Procesar Entregas")
    
    if st.button("🚀 Procesar Entregas", type="primary"):
        with st.spinner("Procesando entregas..."):
            # Extraer nombres CREA
            nombres_crea = [est["nombre_crea"] for est in estudiantes]
            
            # Scrapear entregas
            entregas = scrap_schoology(html_content, nombres_crea)
            
            # Generar estructura de evaluaciones
            evaluaciones = []
            for i, estudiante in enumerate(estudiantes, 1):
                nombre_crea = estudiante["nombre_crea"]
                
                evaluacion = {
                    "numero": i,
                    "nombre": nombre_crea,
                    "resolucion": entregas.get(nombre_crea, "no realiza"),
                    "tarea": consigna_seleccionada_key,
                    "calificacion": {
                        "total": 0,
                        "detalle": [0, 0, 0, 0]
                    },
                    "comentarios": ""
                }
                evaluaciones.append(evaluacion)
            
            # Guardar archivo de entregas
            output_dir = DATA_OUTPUT / curso_seleccionado.get("slug", "default")
            entregas_file = output_dir / f"{consigna_seleccionada_key}_entregas.json"
            
            if save_json(evaluaciones, entregas_file):
                st.success(f"✅ Entregas procesadas y guardadas en: {entregas_file}")
                
                # Mostrar estadísticas
                total_estudiantes = len(evaluaciones)
                estudiantes_entregaron = len([e for e in evaluaciones if e["resolucion"] != "no realiza"])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total estudiantes", total_estudiantes)
                with col2:
                    st.metric("Entregaron", estudiantes_entregaron)
                with col3:
                    st.metric("No entregaron", total_estudiantes - estudiantes_entregaron)
                
                # Mostrar preview de entregas
                st.subheader("📋 Preview de Entregas")
                
                for evaluacion in evaluaciones[:3]:  # Mostrar solo las primeras 3
                    with st.expander(f"👤 {evaluacion['nombre']}"):
                        if evaluacion["resolucion"] != "no realiza":
                            st.text_area(
                                "Entrega:",
                                evaluacion["resolucion"][:500] + "..." if len(evaluacion["resolucion"]) > 500 else evaluacion["resolucion"],
                                height=100,
                                disabled=True
                            )
                        else:
                            st.warning("No realizó la entrega")
                
                # Guardar información del procesamiento en session_state
                st.session_state.entregas_procesadas = evaluaciones
                st.session_state.archivo_entregas = str(entregas_file)
                st.session_state.curso_actual = curso_seleccionado
                st.session_state.consigna_actual = consigna_seleccionada_key
            else:
                st.error("❌ Error guardando las entregas")
    
    # PASO 6: Evaluar con IA (opcional)
    if 'entregas_procesadas' in st.session_state:
        st.markdown("---")
        st.header("6️⃣ Evaluación con IA (Opcional)")
        
        st.info("🤖 **Próximamente:** Evaluación automática con OpenAI GPT-4")
        st.write("Esta funcionalidad permitirá:")
        st.write("- Evaluación automática según rúbrica")
        st.write("- Comentarios personalizados para cada estudiante")
        st.write("- Puntuación detallada por criterio")
        
        # Botón para descargar entregas actuales
        entregas_json = json.dumps(st.session_state.entregas_procesadas, ensure_ascii=False, indent=2)
        
        st.download_button(
            label="📥 Descargar Entregas (JSON)",
            data=entregas_json,
            file_name=f"{st.session_state.consigna_actual}_entregas.json",
            mime="application/json"
        )
        
        st.success(f"✅ Archivo guardado en: {st.session_state.archivo_entregas}")

if __name__ == "__main__":
    main()