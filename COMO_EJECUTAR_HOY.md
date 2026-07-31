# ▶️ Cómo ejecutar el sistema (Windows)

## La forma correcta: doble clic

1. Descomprime el ZIP completo. **Importante:** que no quede dentro de otro ZIP.
   Recomendado: descomprimir en `C:\gyverlabs` (evita problemas de OneDrive y rutas largas).
2. Entra a la carpeta `gyverlabs-showcase`.
3. **Doble clic** en `ejecutar_backend.bat`.
4. La primera vez tarda de 2 a 5 minutos: crea el entorno, instala librerías y genera los datos.
   Verás cada paso en pantalla — es normal que la descarga tarde.
5. Cuando termine, **el navegador se abre solo** con el sistema.
6. Para apagar: cierra la ventana negra.

Las siguientes veces arranca en unos 10 segundos.

---

## ⚠️ No lo ejecutes desde PowerShell con `./`

PowerShell no entiende `./archivo.bat` y da el error *"No se esperaba ... en este momento"*.

Si quieres ejecutarlo desde una terminal, usa **una** de estas formas:

```
.\ejecutar_backend.bat          (PowerShell — con barra invertida)
ejecutar_backend.bat            (CMD — sin nada adelante)
```

Pero lo más simple es el **doble clic**.

---

## 🔧 Si algo sale mal

### La ventana se cierra sola o el sistema no arranca

Ejecuta `REPARAR_TODO.bat` (doble clic), escribe `SI`, y luego vuelve a ejecutar
`ejecutar_backend.bat`. Esto borra el entorno y la base de datos y reinstala todo limpio.
No se pierde ningún archivo del programa.

### Dice que no encuentra Python

1. Descarga Python 3.11 o superior de https://www.python.org/downloads/
2. Al instalar, **marca la casilla `Add Python to PATH`** (está abajo, en la primera pantalla).
3. Reinicia el computador.
4. Vuelve a hacer doble clic en `ejecutar_backend.bat`.

### Dice que no encuentra la carpeta backend

El `.bat` quedó fuera de su carpeta. La estructura correcta es:

```
gyverlabs-showcase\
   backend\
   frontend\
   ejecutar_backend.bat     <-- aquí
   REPARAR_TODO.bat
```

### Falla la instalación de librerías

Suele ser internet o el antivirus. Revisa la conexión, desactiva el antivirus un momento
y vuelve a ejecutar. Si las que fallan son las de **inteligencia artificial**
(pandas, lightgbm), **no pasa nada**: el sistema continúa y usa su modelo de respaldo
por reglas, que clasifica el riesgo casi igual.

---

## 🖐️ Paso a paso manual (si prefieres controlarlo tú)

Abre **CMD** (no PowerShell) en la carpeta del proyecto:

```
cd backend
python -m venv myenv
myenv\Scripts\python.exe -m pip install -r requirements.txt
myenv\Scripts\python.exe preparar_datos.py
myenv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Luego abre `frontend\index.html` con doble clic.

La próxima vez solo necesitas la última línea.

---

## 🐧 Linux / macOS

```
bash ejecutar_backend.sh
```

Y abre `frontend/index.html` en el navegador.

---

## 🔄 Regenerar los datos desde cero

```
cd backend
myenv\Scripts\python.exe preparar_datos.py --reset
```

Esto borra la base y la vuelve a generar con datos nuevos.

---

## 👥 Perfiles disponibles en la demo

Al abrir el sistema aparece el selector de perfiles. Son **10**:

| Perfil | Qué demuestra |
|---|---|
| 🧠 Súper Admin | Crea instituciones y secretarías, sube el logo de cada una (marca blanca) |
| 🎒 **Alumno** | Portal del estudiante: clases, tareas, notas, curso de Contabilidad, clases en vivo |
| 👨‍🏫 Docente | Asistencia, aula virtual con IA, calendario, notas, su hoja de vida |
| 📋 Coordinación | Alertas del día, solicitudes de salón, docentes |
| 🎓 Rectoría | Todo el colegio: personal, FSE, contratación, pagos, comunicados |
| 🗂️ Contratación | Expedientes de contratistas y documentos |
| 🧮 Contaduría | CDP/RP, libro FSE, cuentas por pagar |
| ⚖️ Jurídica | Revisión legal de contratos con validación automática |
| 🏛️ Secretaría | Consolidado territorial y censo juvenil |
| 🇨🇴 Ministerio | Panorama nacional |

Todos los datos son **simulados**: ninguna acción sale del computador.
