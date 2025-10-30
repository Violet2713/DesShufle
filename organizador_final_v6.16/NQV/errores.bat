@echo off
echo --- MODO DE DEPURACION ---
echo (Esta ventana NO se cerrara sola para que puedas ver los errores)
echo.

REM Ir a la carpeta del script
cd /d "%~dp0"

REM Ejecutar app.py de forma visible
py app.py

echo.
echo --- El servidor se ha detenido (o ha fallado) ---
pause
