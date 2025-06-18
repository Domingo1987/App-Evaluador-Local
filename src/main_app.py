import streamlit as st
import json
import os
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Evaluación Automática",
    page_icon="📝",
    layout="wide"
)

# CSS personalizado para estilos
st.markdown("""
<style>
.student-card {
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    padding: 15px;
    margin: 10px 0;
    background-color: white;
}

.student-no-delivery {
    border-color: #ff4444;
    background-color: #ffe6e6;
}

.student-delivered {
    border-color: #44ff44;
    background-color: #e6ffe6;
}

.student-pending {
    border-color: #ffaa44;
    background-color: #fff0e6;
}

.student-evaluated {
    border-color: #4444ff;
    background-color: #e6e6ff;
}

.metric-container {
    display: flex;
    justify-content: space-around;
    margin: 20px 0;
}

.status-badge {
    padding: 5px 10px;
    border-radius: 15px;
    color: white;
    font-size: 12px;
    font-weight: bold;
}

.status-no-delivery {
    background-color: #ff4444;
}

.status-delivered {
    background-color: #ffaa44;
}

.status-evaluated {
    background-color: #4444ff;
}
</style>
""", unsafe_allow_html=True)

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

def get_student_status(evaluacion):
    """Determina el estado de un estudiante"""
    if evaluacion["resolucion"] == "no realiza":
        return "no_entrega", "No Entregó"
    elif evaluacion["calificacion"]["total"] == 0:
        return "entregado", "Entregado"
    else:
        return "evaluado", "Evaluado"

def render_student_card(evaluacion, index):
    """Renderiza una tarjeta de estudiante"""
    status_code, status_text = get_student_status(evaluacion)
    
    # Determinar clase CSS
    if status_code == "no_entrega":
        card_class = "student-no-delivery"
        badge_class = "status-no-delivery"
    elif status_code == "entregado":
        card_class = "student-pending"
        badge_class = "status-delivered"
    else:
        card_class = "student-evaluated"
        badge_class = "status-evaluated"
    
    # HTML de la tarjeta
    card_html = f"""
    <div class="student-card {card_class}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h4>👤 {evaluacion['nombre']}</h4>
            <span class="status-badge {badge_class}">{status_text}</span>
        </div>
        <p><strong>Tarea:</strong> {evaluacion['tarea']}</p>
        <p><strong>Calificación:</strong> {evaluacion['calificacion']['total']}/10</p>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)

def evaluate_student_interface(evaluacion, index):
    """Interfaz para evaluar un estudiante individual"""
    st.markdown(f"### 📝 Evaluando: {evaluacion['nombre']}")
    
    # Mostrar entrega
    if evaluacion["resolucion"] != "no realiza":
        with st.expander("Ver entrega completa", expanded=True):
            st.text_area(
                "Entrega del estudiante:",
                evaluacion["resolucion"],
                height=200,
                disabled=True,
                key=f"entrega_{index}"
            )
    else:
        st.error("❌ El estudiante no realizó la entrega")
        return evaluacion
    
    # Formulario de evaluación
    with st.form(key=f"eval_form_{index}"):
        st.subheader("Calificación por criterios:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            criterio1 = st.slider("Criterio 1 (Comprensión)", 0, 3, evaluacion["calificacion"]["detalle"][0], key=f"c1_{index}")
            criterio2 = st.slider("Criterio 2 (Implementación)", 0, 3, evaluacion["calificacion"]["detalle"][1], key=f"c2_{index}")
        
        with col2:
            criterio3 = st.slider("Criterio 3 (Documentación)", 0, 2, evaluacion["calificacion"]["detalle"][2], key=f"c3_{index}")
            criterio4 = st.slider("Criterio 4 (Presentación)", 0, 2, evaluacion["calificacion"]["detalle"][3], key=f"c4_{index}")
        
        total_calculado = criterio1 + criterio2 + criterio3 + criterio4
        st.metric("Total calculado", f"{total_calculado}/10")
        
        # Comentarios
        comentarios = st.text_area(
            "Comentarios para el estudiante:",
            evaluacion["comentarios"],
            height=100,
            key=f"comments_{index}"
        )
        
        # Botones
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            submit_eval = st.form_submit_button("💾 Guardar Evaluación", type="primary")
        
        with col_btn2:
            skip_eval = st.form_submit_button("⏭️ Saltar")
        
        with col_btn3:
            auto_eval = st.form_submit_button("🤖 Evaluación IA", disabled=True)
        
        if submit_eval:
            # Validar que tenga nota si entregó
            if total_calculado == 0 and evaluacion["resolucion"] != "no realiza":
                st.warning("⚠️ El estudiante entregó pero la calificación es 0. ¿Está seguro?")
                confirmar = st.button("Sí, confirmar calificación 0", key=f"confirm_{index}")
                if not confirmar:
                    st.stop()
            
            # Actualizar evaluación
            evaluacion["calificacion"]["total"] = total_calculado
            evaluacion["calificacion"]["detalle"] = [criterio1, criterio2, criterio3, criterio4]
            evaluacion["comentarios"] = comentarios
            
            st.success("✅ Evaluación guardada")
            return evaluacion, True
        
        elif skip_eval:
            st.info("⏭️ Estudiante saltado")
            return evaluacion, True
    
    return evaluacion, False

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
                
                # Guardar información del procesamiento en session_state
                st.session_state.entregas_procesadas = evaluaciones
                st.session_state.archivo_entregas = str(entregas_file)
                st.session_state.curso_actual = curso_seleccionado
                st.session_state.consigna_actual = consigna_seleccionada_key
            else:
                st.error("❌ Error guardando las entregas")
    
    # PASO 6: Vista General de Estudiantes
    if 'entregas_procesadas' in st.session_state:
        st.markdown("---")
        st.header("6️⃣ Vista General de Estudiantes")
        
        evaluaciones = st.session_state.entregas_procesadas
        
        # Estadísticas por estado
        no_entregaron = len([e for e in evaluaciones if get_student_status(e)[0] == "no_entrega"])
        entregaron = len([e for e in evaluaciones if get_student_status(e)[0] == "entregado"])
        evaluados = len([e for e in evaluaciones if get_student_status(e)[0] == "evaluado"])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", len(evaluaciones))
        with col2:
            st.metric("No Entregaron", no_entregaron)
        with col3:
            st.metric("Pendientes", entregaron)
        with col4:
            st.metric("Evaluados", evaluados)
        
        # Vista de tarjetas
        st.subheader("📋 Estado de los Estudiantes")
        
        for i, evaluacion in enumerate(evaluaciones):
            render_student_card(evaluacion, i)
        
        st.markdown("---")
        
        # PASO 7: Evaluación Individual
        st.header("7️⃣ Evaluación Individual")
        
        # Inicializar índice si no existe
        if 'current_student_index' not in st.session_state:
            st.session_state.current_student_index = 0
        
        # Controles de navegación
        col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
        
        with col_nav1:
            if st.button("⏮️ Primero") and st.session_state.current_student_index > 0:
                st.session_state.current_student_index = 0
                st.rerun()
        
        with col_nav2:
            if st.button("◀️ Anterior") and st.session_state.current_student_index > 0:
                st.session_state.current_student_index -= 1
                st.rerun()
        
        with col_nav3:
            if st.button("▶️ Siguiente") and st.session_state.current_student_index < len(evaluaciones) - 1:
                st.session_state.current_student_index += 1
                st.rerun()
        
        with col_nav4:
            if st.button("⏭️ Último") and st.session_state.current_student_index < len(evaluaciones) - 1:
                st.session_state.current_student_index = len(evaluaciones) - 1
                st.rerun()
        
        # Selector directo
        estudiante_nombres = [f"{i+1}. {e['nombre']}" for i, e in enumerate(evaluaciones)]
        selected_index = st.selectbox(
            "Ir directamente a:",
            range(len(estudiante_nombres)),
            index=st.session_state.current_student_index,
            format_func=lambda x: estudiante_nombres[x]
        )
        
        if selected_index != st.session_state.current_student_index:
            st.session_state.current_student_index = selected_index
            st.rerun()
        
        # Mostrar progreso
        progreso = (st.session_state.current_student_index + 1) / len(evaluaciones)
        st.progress(progreso, text=f"Estudiante {st.session_state.current_student_index + 1} de {len(evaluaciones)}")
        
        # Interfaz de evaluación
        current_evaluacion = evaluaciones[st.session_state.current_student_index]
        
        try:
            evaluacion_actualizada, continuar = evaluate_student_interface(current_evaluacion, st.session_state.current_student_index)
            
            # Actualizar la evaluación en la lista
            st.session_state.entregas_procesadas[st.session_state.current_student_index] = evaluacion_actualizada
            
            # Guardar automáticamente
            if continuar:
                output_dir = DATA_OUTPUT / st.session_state.curso_actual.get("slug", "default")
                entregas_file = output_dir / f"{st.session_state.consigna_actual}_entregas.json"
                
                if save_json(st.session_state.entregas_procesadas, entregas_file):
                    # Auto-avanzar al siguiente estudiante pendiente
                    next_pending = None
                    for i in range(st.session_state.current_student_index + 1, len(evaluaciones)):
                        if get_student_status(evaluaciones[i])[0] == "entregado":
                            next_pending = i
                            break
                    
                    if next_pending is not None:
                        st.session_state.current_student_index = next_pending
                        time.sleep(1)  # Pequeña pausa
                        st.rerun()
                    else:
                        st.success("🎉 ¡Todas las evaluaciones completadas!")
                        
        except Exception as e:
            st.error(f"❌ Error en la evaluación: {e}")
            st.info("🔄 Reintentando en 3 segundos...")
            time.sleep(3)
            st.rerun()
        
        # Descarga final
        st.markdown("---")
        st.subheader("📥 Descargar Resultados")
        
        entregas_json = json.dumps(st.session_state.entregas_procesadas, ensure_ascii=False, indent=2)
        
        st.download_button(
            label="📥 Descargar Evaluaciones Completas (JSON)",
            data=entregas_json,
            file_name=f"{st.session_state.consigna_actual}_evaluaciones_completas.json",
            mime="application/json"
        )
        
        # Generar CSV para calificaciones
        df_calificaciones = pd.DataFrame([
            {
                "Nombre": e["nombre"],
                "Tarea": e["tarea"],
                "Estado": get_student_status(e)[1],
                "Calificación": e["calificacion"]["total"],
                "Criterio 1": e["calificacion"]["detalle"][0],
                "Criterio 2": e["calificacion"]["detalle"][1],
                "Criterio 3": e["calificacion"]["detalle"][2],
                "Criterio 4": e["calificacion"]["detalle"][3],
                "Comentarios": e["comentarios"]
            }
            for e in st.session_state.entregas_procesadas
        ])
        
        csv_data = df_calificaciones.to_csv(index=False, encoding='utf-8')
        
        st.download_button(
            label="📊 Descargar Calificaciones (CSV)",
            data=csv_data,
            file_name=f"{st.session_state.consigna_actual}_calificaciones.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()