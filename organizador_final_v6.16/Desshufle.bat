@echo off
REM Ir a la carpeta del script
cd /d "%~dp0"

REM Ejecutar el Python que esta DENTRO de venv, en modo invisible
START "Desshufle" /B ".\venv\Scripts\python.exe" app.py
exit
