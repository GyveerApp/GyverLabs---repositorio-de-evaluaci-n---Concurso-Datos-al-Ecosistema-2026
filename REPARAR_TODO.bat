@echo off
setlocal
title GyverLabs - Reparar instalacion
cd /d "%~dp0"

cls
echo ================================================================
echo    GYVERLABS - REPARAR INSTALACION
echo ================================================================
echo.
echo  Usa este archivo cuando:
echo    - La instalacion quedo a medias.
echo    - El sistema no arranca o da errores raros.
echo    - Quieres volver a empezar con datos frescos.
echo.
echo  Que voy a borrar:
echo    - La carpeta myenv       [el entorno de Python]
echo    - La base de datos       [gyverlabs_demo.db]
echo.
echo  NO se borra ningun archivo del programa.
echo  Despues de reparar, ejecuta:  ejecutar_backend.bat
echo.
echo ----------------------------------------------------------------
echo.
set /p RESP="Escribe SI y presiona Enter para continuar: "

if /i "%RESP%"=="SI" goto REPARAR
echo.
echo Cancelado. No se borro nada.
echo.
pause
goto FIN

:REPARAR
echo.
if not exist "backend\main.py" goto ERROR_CARPETA
cd backend

echo Borrando el entorno virtual...
if exist "myenv" rmdir /s /q "myenv"
if exist "myenv" goto ERROR_BORRAR
echo    Entorno borrado.
echo.

echo Borrando la base de datos...
if exist "gyverlabs_demo.db" del /q "gyverlabs_demo.db"
if exist "datos\*.jsonl" del /q "datos\*.jsonl"
if exist "datos\*.csv" del /q "datos\*.csv"
echo    Base de datos borrada.
echo.

echo Borrando archivos temporales de Python...
for /d /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"
echo    Temporales borrados.
echo.

echo ================================================================
echo    REPARACION COMPLETA
echo ================================================================
echo.
echo  Ahora haz doble clic en:   ejecutar_backend.bat
echo  Se reinstalara todo desde cero.
echo.
pause
goto FIN

:ERROR_CARPETA
echo.
echo ERROR: no encontre la carpeta backend.
echo Este archivo debe estar junto a las carpetas backend y frontend.
echo.
pause
goto FIN

:ERROR_BORRAR
echo.
echo ================================================================
echo    NO PUDE BORRAR LA CARPETA myenv
echo ================================================================
echo.
echo  Casi siempre es porque el servidor sigue abierto.
echo.
echo  Solucion:
echo   1. Cierra TODAS las ventanas negras de GyverLabs.
echo   2. Vuelve a ejecutar este archivo.
echo.
echo  Si sigue fallando, borra a mano la carpeta:
echo     backend\myenv
echo.
pause
goto FIN

:FIN
endlocal
