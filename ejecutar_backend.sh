#!/bin/bash
# Levanta el backend de GyverLabs localmente (sin Docker) para la demo.
# Crea/activa el entorno virtual "myenv", instala dependencias, genera
# el dataset sintético, entrena el modelo demo, y arranca el servidor.
#
# Uso:
#   chmod +x ejecutar_backend.sh
#   ./ejecutar_backend.sh
#
set -e

cd "$(dirname "$0")/backend"

if [ ! -d "myenv" ]; then
  echo "Creando entorno virtual 'myenv'..."
  python3 -m venv myenv
fi

source myenv/bin/activate
echo "Instalando dependencias (primera vez puede tardar 1-2 minutos)..."
pip install -q -r requirements.txt

if [ ! -f "gyverlabs_demo.db" ]; then
  echo "Generando el dataset sintético de demostración..."
  python seed_data.py
fi

if [ ! -f "ml/demo_model.txt" ]; then
  echo "Entrenando el modelo demo (LightGBM)..."
  python ml/train_demo.py
fi

echo ""
echo "============================================================"
echo " GyverLabs backend corriendo en http://localhost:8000"
echo " Documentación interactiva (Swagger): http://localhost:8000/docs"
echo " Deja esta ventana abierta y abre frontend/index.html en el navegador"
echo "============================================================"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
