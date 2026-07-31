#!/usr/bin/env bash
# GyverLabs - arranque para Linux / macOS
# Uso:  bash ejecutar_backend.sh
set -e
cd "$(dirname "$0")"

echo "================================================================"
echo "   GYVERLABS - SISTEMA EDUCATIVO INTELIGENTE"
echo "================================================================"
echo ""
echo "Carpeta de trabajo: $(pwd)"
echo ""

# --- Paso 1: Python ---
echo "[PASO 1 de 5] Buscando Python..."
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "ERROR: no encontre Python 3. Instalalo con: sudo apt install python3 python3-venv"
  exit 1
fi
echo "   $($PY --version)"
echo ""

# --- Paso 2: carpeta backend ---
echo "[PASO 2 de 5] Entrando a backend..."
if [ ! -f "backend/main.py" ]; then
  echo "ERROR: no encontre backend/main.py. Ejecuta este script desde la carpeta del proyecto."
  exit 1
fi
cd backend
echo "   OK: $(pwd)"
echo ""

# --- Paso 3: entorno virtual ---
echo "[PASO 3 de 5] Preparando entorno virtual..."
if [ ! -f "myenv/bin/python" ]; then
  echo "   Creando entorno virtual..."
  $PY -m venv myenv
fi
VPY="$(pwd)/myenv/bin/python"
if [ ! -f "$VPY" ]; then
  echo "ERROR: no se pudo crear el entorno. Instala: sudo apt install python3-venv"
  exit 1
fi
echo "   OK: $VPY"
echo ""

# --- Paso 4: librerias ---
echo "[PASO 4 de 5] Instalando librerias..."
"$VPY" -m pip install --upgrade pip --disable-pip-version-check
echo ""
echo "   --- Parte A: obligatorias ---"
"$VPY" -m pip install --disable-pip-version-check \
  fastapi==0.111.0 "uvicorn[standard]==0.30.1" sqlalchemy==2.0.30 \
  pydantic==2.7.1 pydantic-settings==2.2.1 python-multipart==0.0.9 \
  "passlib[bcrypt]==1.7.4" "python-jose[cryptography]==3.3.0"
echo ""
echo "   --- Parte B: IA (opcionales) ---"
if ! "$VPY" -m pip install --disable-pip-version-check pandas numpy scikit-learn lightgbm; then
  echo "   AVISO: fallaron las librerias de IA. El sistema usara su modelo de respaldo."
fi
echo ""

# --- Paso 5: base de datos ---
echo "[PASO 5 de 5] Preparando la base de datos..."
if [ ! -f "gyverlabs_demo.db" ]; then
  "$VPY" preparar_datos.py
else
  echo "   Ya existe. Para regenerarla: $VPY preparar_datos.py --reset"
fi
echo ""

echo "================================================================"
echo "   TODO LISTO - INICIANDO EL SERVIDOR"
echo "================================================================"
echo ""
echo "  Servidor:  http://127.0.0.1:8000"
echo "  Abre en el navegador:  frontend/index.html"
echo "  Para apagar: Ctrl + C"
echo ""

"$VPY" -m uvicorn main:app --host 127.0.0.1 --port 8000
