@echo off
echo ==========================================================
echo    Instalador de Dependencias para Desshufle
echo ==========================================================
echo.
echo Creando un entorno virtual (mochila) en la carpeta 'venv'...
echo (Esto puede tardar un momento)

REM Ir a la carpeta del script
cd /d "%~dp0"

REM --- (BLOQUE CORREGIDO) ---
REM Intentar crear el entorno virtual, primero con 'py'
py -m venv venv

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo "'py' no funciono. Intentando con 'python'..."
    REM Si 'py' falla, intentar con 'python'
    python -m venv venv
    
    IF %ERRORLEVEL% NEQ 0 (
        echo.
        echo ERROR: No se pudo crear el entorno virtual ni con 'py' ni con 'python'.
        echo Asegurate de tener Python 3.10 o superior instalado.
        echo.
        echo Al instalar Python, ASEGURATE de marcar la casilla que dice:
        echo "Add Python to PATH"
        echo.
        pause
        exit /b 1
    )
)
echo.
echo Entorno 'venv' creado.
echo Instalando librerias (Flask, Pandas, Matplotlib) desde requirements.txt...
echo Esto puede tardar unos minutos. Por favor, espera...

REM --- (LINEA CORREGIDA) ---
REM Le damos a pip la RUTA COMPLETA al requirements.txt usando "%~dp0"
CALL ".\\venv\\Scripts\\pip.exe" install -r "%~dp0requirements.txt"

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Fallo la instalacion de las librerias.
    echo El error NO es de internet. Probablemente el script no encontro 'requirements.txt'.
    echo Asegurate de que 'requirements.txt' esta en la misma carpeta que este instalador.
    pause
    exit /b 1
)

echo.
echo ==========================================================
echo    ¡Instalacion completada con exito!
echo ==========================================================
echo.
echo Ya puedes cerrar esta ventana.
echo.
echo Para usar la aplicacion, haz doble clic en 'Desshufle.bat'.
echo.
pause

