@echo off
echo --- MODO DE DEPURACION (usando 'venv') ---
echo (Esta ventana NO se cerrara sola para que puedas ver los errores)
echo.

REM Ir a la carpeta del script
cd /d "%~dp0"

REM Activar el venv y ejecutar app.py de forma visible
call ".\venv\Scripts\activate.bat"
py app.py

echo.
echo --- El servidor se ha detenido (o ha fallado) ---
pause
