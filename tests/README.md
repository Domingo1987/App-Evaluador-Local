# Pruebas automatizadas

Este proyecto utiliza **pytest** para ejecutar las pruebas de la aplicación que se encuentra en `src/`.

## Preparación del entorno

1. (Opcional) Crea y activa un entorno virtual:
   ```bash
   ./setup.sh
   source .venv/bin/activate
   ```
2. Instala las dependencias del proyecto:
   ```bash
   pip install -r requirements.txt
   ```

## Ejecución de las pruebas

Desde la raíz del repositorio ejecuta:
```bash
pytest -v
```
Esto ejecutará todos los tests ubicados en la carpeta `tests/`.
