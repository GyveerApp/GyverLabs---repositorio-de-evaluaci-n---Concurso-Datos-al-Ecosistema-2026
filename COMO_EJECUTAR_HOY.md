# Cómo ejecutar la demo — paso a paso

Esto te deja el sistema completo corriendo en tu computador: backend real (API + modelo de IA entrenado) y el dashboard en el navegador. Tiempo estimado: 3-5 minutos la primera vez.

---

## Opción A — Automática (recomendada)

**Mac / Linux:**
```bash
cd gyverlabs-showcase
chmod +x ejecutar_backend.sh
./ejecutar_backend.sh
```

**Windows:**
```
cd gyverlabs-showcase
ejecutar_backend.bat
```

Esto crea el entorno virtual `myenv`, instala todo, genera los datos sintéticos, entrena el modelo, y deja el servidor corriendo. Cuando veas el mensaje `GyverLabs backend corriendo en http://localhost:8000`, sigue al **Paso final** más abajo.

---

## Opción B — Manual, paso a paso (para entender o si la automática falla)

### 1. Abre una terminal en la carpeta del proyecto
```bash
cd gyverlabs-showcase/backend
```

### 2. Crea el entorno virtual llamado `myenv`
```bash
python3 -m venv myenv
```
(En Windows usa `python` en vez de `python3` si `python3` no se reconoce.)

### 3. Actívalo
```bash
# Mac / Linux
source myenv/bin/activate

# Windows (cmd)
myenv\Scripts\activate.bat

# Windows (PowerShell)
myenv\Scripts\Activate.ps1
```
Cuando está activo, ves `(myenv)` al inicio de la línea de tu terminal.

### 4. Instala las dependencias
```bash
pip install -r requirements.txt
```

### 5. Genera el conjunto de datos sintético (una sola vez)
```bash
python seed_data.py
```
Esto crea `gyverlabs_demo.db` con 840 estudiantes simulados, su historial de asistencia, notas, los movimientos contables del FSE, y el censo juvenil territorial (440 jóvenes simulados en 8 municipios de Santander y Bolívar). Ningún dato es real.

### 6. Entrena el modelo de IA (una sola vez)
```bash
python ml/train_demo.py
```
Esto entrena un LightGBM real sobre los datos sintéticos y muestra las métricas reales (AUC-ROC, precisión, recall) en la terminal — cópialas, las necesitas para la sección de Resultados del documento y la presentación.

### 7. Levanta el servidor
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Déjalo corriendo. Verifica que funciona abriendo en el navegador: **http://localhost:8000/docs** — ahí ves la documentación interactiva (Swagger) de toda la API, y puedes probar cada endpoint en vivo, en frente del jurado si lo piden.

---

## Paso final — abrir el dashboard (ambas opciones)

1. Deja la terminal del backend abierta y corriendo.
2. Ve a la carpeta `gyverlabs-showcase/frontend`.
3. Abre el archivo `index.html` haciendo doble clic (o clic derecho → "Abrir con" → tu navegador).
4. En la pantalla de login, el correo y la contraseña ya vienen precargados — solo haz clic en **"Ingresar al panel"**.
5. Mira la esquina inferior izquierda del panel: si dice **🟢 Conectado al backend en vivo**, el dashboard está mostrando datos reales calculados en ese momento por el modelo. Si por algún motivo el backend no responde, verás **🟡 Modo local** y el dashboard sigue funcionando igual, con datos de respaldo — la demo nunca se cae.

---

## Verificación rápida antes de salir a presentar

Corre esto y confirma que las 4 líneas dicen `200`:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/srd/tablero
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/fse/resumen
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/censo/resumen
```

## Si algo falla

- **"python3: command not found"** → instala Python 3.10+ desde python.org, o usa `python` en vez de `python3`.
- **El navegador no carga los datos en vivo (queda en 🟡 modo local)** → revisa que la terminal del backend siga abierta y sin errores; revisa que dice `Uvicorn running on http://0.0.0.0:8000`.
- **Puerto 8000 ocupado** → cierra cualquier otro proceso usando ese puerto, o cambia `--port 8000` por `--port 8001` en el comando y en `API_BASE` dentro de `frontend/index.html`.
- **Quieres reiniciar con datos "frescos"** → borra `backend/gyverlabs_demo.db` y `backend/ml/demo_model.txt`, y repite los pasos 5 y 6.
