#!/bin/bash

# Detener ejecución si hay un error
set -e

echo "Creando entorno virtual (.venv)..."
python3 -m venv .venv

echo "Activando entorno virtual..."
source .venv/bin/activate

echo "Actualizando pip..."
pip install --upgrade pip

if [ -f requirements.txt ]; then
    echo "Instalando dependencias desde requirements.txt..."
    pip install -r requirements.txt
else
    echo "No se encontró requirements.txt, omitiendo instalación de dependencias."
fi

echo "Listo. Entorno virtual y dependencias instaladas."
echo "Recuerda activar el entorno con: source .venv/bin/activate"
