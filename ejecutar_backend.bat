@echo off
REM Levanta el backend de GyverLabs localmente (Windows) para la demo.
REM Crea/activa el entorno virtual "myenv", instala dependencias, genera
REM el dataset sintetico, entrena el modelo demo, y arranca el servidor.

cd /d "%~dp0backend"

if not exist "myenv" (
  echo Creando entorno virtual 'myenv'...
  python -m venv myenv
)

call myenv\Scripts\activate.bat

echo Instalando dependencias...
pip install -q -r requirements.txt

if not exist "gyverlabs_demo.db" (
  echo Generando el dataset sintetico de demostracion...
  python seed_data.py
)

if not exist "ml\demo_model.txt" (
  echo Entrenando el modelo demo...
  python ml\train_demo.py
)

echo.
echo ============================================================
echo  GyverLabs backend corriendo en http://localhost:8000
echo  Documentacion interactiva: http://localhost:8000/docs
echo  Deja esta ventana abierta y abre frontend\index.html en el navegador
echo ============================================================
echo.

uvicorn main:app --reload --host 0.0.0.0 --port 8000
