@echo off
setlocal
title GyverLabs - Sistema Educativo Inteligente
cd /d "%~dp0"

cls
echo ================================================================
echo    GYVERLABS - SISTEMA EDUCATIVO INTELIGENTE
echo    Instalacion y arranque automatico para Windows
echo ================================================================
echo.
echo  Carpeta de trabajo:
echo    %CD%
echo.
echo  Este proceso tarda de 2 a 5 minutos la PRIMERA vez.
echo  Las siguientes veces arranca en 10 segundos.
echo.
echo  IMPORTANTE: no cierres esta ventana mientras uses el sistema.
echo.
echo ----------------------------------------------------------------
echo.

REM ============================================================
REM  PASO 1 - Buscar Python instalado
REM ============================================================
echo [PASO 1 de 5] Buscando Python en tu equipo...
echo.

set "PYEXE="

python --version >nul 2>&1
if not errorlevel 1 set "PYEXE=python"
if defined PYEXE goto PYTHON_OK

py -3 --version >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3"
if defined PYEXE goto PYTHON_OK

python3 --version >nul 2>&1
if not errorlevel 1 set "PYEXE=python3"
if defined PYEXE goto PYTHON_OK

goto ERROR_PYTHON

:PYTHON_OK
echo    Python encontrado. Version:
%PYEXE% --version
echo.

REM ============================================================
REM  PASO 2 - Entrar a la carpeta backend
REM ============================================================
echo [PASO 2 de 5] Entrando a la carpeta backend...
if not exist "backend\main.py" goto ERROR_CARPETA
cd backend
echo    OK. Ahora estoy en:
echo    %CD%
echo.

REM ============================================================
REM  PASO 3 - Crear el entorno virtual
REM ============================================================
echo [PASO 3 de 5] Preparando el entorno virtual...
echo.

if exist "myenv\Scripts\python.exe" goto VENV_LISTO

echo    No existe el entorno. Creandolo ahora...
echo    Esto puede tardar un minuto. Espera por favor.
echo.
%PYEXE% -m venv myenv
echo.

if not exist "myenv\Scripts\python.exe" goto ERROR_VENV

echo    Entorno virtual creado correctamente.
echo.
goto VENV_CONTINUAR

:VENV_LISTO
echo    El entorno virtual ya existe. Lo reutilizo.
echo.

:VENV_CONTINUAR
set "VPY=%CD%\myenv\Scripts\python.exe"
echo    Python del entorno:
echo    %VPY%
echo.

REM ============================================================
REM  PASO 4 - Instalar las librerias
REM ============================================================
echo [PASO 4 de 5] Instalando librerias necesarias...
echo    Veras la descarga en pantalla. Es normal que tarde.
echo.

"%VPY%" -m pip install --upgrade pip --disable-pip-version-check
echo.

echo    --- Parte A: librerias del sistema, obligatorias ---
echo.
"%VPY%" -m pip install --disable-pip-version-check fastapi==0.111.0 "uvicorn[standard]==0.30.1" sqlalchemy==2.0.30 pydantic==2.7.1 pydantic-settings==2.2.1 python-multipart==0.0.9 "passlib[bcrypt]==1.7.4" "python-jose[cryptography]==3.3.0"
if errorlevel 1 goto ERROR_PIP

echo.
echo    --- Parte B: librerias de inteligencia artificial, opcionales ---
echo        Si alguna falla, el sistema funciona igual con su modelo de respaldo.
echo.
"%VPY%" -m pip install --disable-pip-version-check pandas numpy scikit-learn lightgbm
if errorlevel 1 goto AVISO_IA
echo.
echo    Todas las librerias se instalaron correctamente.
echo.
goto PIP_LISTO

:AVISO_IA
echo.
echo    AVISO: no se pudieron instalar las librerias de IA.
echo    Esto NO detiene el sistema: usara su modelo de respaldo por reglas,
echo    que clasifica el riesgo casi igual que el modelo entrenado.
echo    Puedes continuar sin problema.
echo.

:PIP_LISTO

REM ============================================================
REM  PASO 5 - Preparar la base de datos
REM ============================================================
echo [PASO 5 de 5] Preparando la base de datos...
echo.

if exist "gyverlabs_demo.db" goto DB_LISTA

echo    Generando datos de demostracion. Tarda 1 o 2 minutos.
echo.
"%VPY%" preparar_datos.py
if errorlevel 1 goto ERROR_DB
if not exist "gyverlabs_demo.db" goto ERROR_DB
goto DB_CONTINUAR

:DB_LISTA
echo    La base de datos ya existe. La reutilizo.
echo    Si quieres regenerarla, usa el archivo REPARAR_TODO.bat
echo.

:DB_CONTINUAR
echo.
echo ================================================================
echo    TODO LISTO - INICIANDO EL SERVIDOR
echo ================================================================
echo.
echo  El sistema abrira solo en tu navegador.
echo  Si no abre, haz doble clic en el archivo:
echo     frontend\index.html
echo.
echo  Direccion del servidor:  http://127.0.0.1:8000
echo  Documentacion tecnica:   http://127.0.0.1:8000/docs
echo.
echo  Para APAGAR el sistema: cierra esta ventana.
echo.
echo ----------------------------------------------------------------
echo.

start "" "%~dp0frontend\index.html"

"%VPY%" -m uvicorn main:app --host 127.0.0.1 --port 8000

echo.
echo El servidor se detuvo.
pause
goto FIN


REM ============================================================
REM  MENSAJES DE ERROR - cada uno se queda en pantalla
REM ============================================================

:ERROR_PYTHON
echo.
echo ================================================================
echo    NO ENCONTRE PYTHON EN TU EQUIPO
echo ================================================================
echo.
echo  Que hacer:
echo.
echo   1. Entra a:  https://www.python.org/downloads/
echo   2. Descarga Python 3.11 o superior.
echo   3. Al instalarlo, MARCA la casilla que dice:
echo         Add Python to PATH
echo      Esa casilla esta abajo en la primera pantalla del instalador.
echo   4. Termina la instalacion y REINICIA el computador.
echo   5. Vuelve a hacer doble clic en este archivo.
echo.
pause
goto FIN

:ERROR_CARPETA
echo.
echo ================================================================
echo    NO ENCONTRE LA CARPETA backend
echo ================================================================
echo.
echo  Este archivo debe estar en la carpeta principal, junto a las
echo  carpetas backend y frontend. Deberia verse asi:
echo.
echo     gyverlabs-showcase\
echo        backend\
echo        frontend\
echo        ejecutar_backend.bat     ^<-- este archivo
echo.
echo  Carpeta donde me ejecutaron:
echo     %CD%
echo.
echo  Solucion: descomprime el ZIP completo y ejecuta el .bat que
echo  quedo dentro de la carpeta gyverlabs-showcase.
echo.
pause
goto FIN

:ERROR_VENV
echo.
echo ================================================================
echo    NO SE PUDO CREAR EL ENTORNO VIRTUAL
echo ================================================================
echo.
echo  Causas mas comunes y como resolverlas:
echo.
echo   1. El antivirus bloqueo la creacion de archivos.
echo      Desactivalo un momento y vuelve a intentar.
echo.
echo   2. La carpeta esta en OneDrive o en el Escritorio sincronizado.
echo      Mueve la carpeta a un lugar simple como:
echo         C:\gyverlabs
echo      y ejecuta el .bat desde ahi.
echo.
echo   3. Falta el modulo venv de Python.
echo      Reinstala Python marcando la casilla Add Python to PATH.
echo.
echo  Para ver el error exacto, abre CMD en esta carpeta y escribe:
echo      %PYEXE% -m venv myenv
echo.
pause
goto FIN

:ERROR_PIP
echo.
echo ================================================================
echo    FALLO LA INSTALACION DE LIBRERIAS
echo ================================================================
echo.
echo  Causas mas comunes:
echo.
echo   1. No hay internet o se corto la conexion.
echo      Revisa tu conexion y vuelve a ejecutar este archivo.
echo.
echo   2. El antivirus o el firewall bloqueo la descarga.
echo.
echo   3. Quedo a medias una instalacion anterior.
echo      Ejecuta el archivo REPARAR_TODO.bat y vuelve a intentar.
echo.
echo  El detalle del error aparece mas arriba en esta misma ventana.
echo  Desplazate hacia arriba para leerlo.
echo.
pause
goto FIN

:ERROR_DB
echo.
echo ================================================================
echo    NO SE PUDO CREAR LA BASE DE DATOS
echo ================================================================
echo.
echo  El detalle del error aparece mas arriba en esta ventana.
echo  Desplazate hacia arriba para leerlo.
echo.
echo  Solucion recomendada:
echo   1. Ejecuta el archivo REPARAR_TODO.bat
echo   2. Vuelve a ejecutar este archivo.
echo.
pause
goto FIN

:FIN
endlocal
