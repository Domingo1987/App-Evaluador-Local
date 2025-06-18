# App-Evaluador-Local

Esta aplicación procesa entregas de estudiantes y permite evaluarlas con la API de OpenAI.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

### Aplicación principal

Ejecuta la interfaz en Streamlit:

```bash
streamlit run src/main_app.py
```

### Evaluación por línea de comandos

También puedes evaluar un archivo JSON directamente:

```bash
python src/evaluar_chat.py input.json output.json
```

`input.json` debe contener una lista de entregas con los campos `nombre`, `resolucion` y `tarea`.

## Pruebas

```bash
pytest -v
```
