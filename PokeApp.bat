@echo off
setlocal
cd /d "%~dp0"

echo ================================
echo   Iniciando Liga Pokemon App
echo ================================
echo.

REM (Opcional) activa tu venv si usas uno:
REM call venv\Scripts\activate

REM Por si .NET hiciera falta en algun paso externo (no estorba):
set "DOTNET_ROOT=C:\Program Files\dotnet"
set "PATH=%DOTNET_ROOT%;%PATH%"

REM Buscar puerto libre 8501..8510 para evitar "is already in use"
set PORT=
for /L %%P in (8501,1,8510) do (
  netstat -ano | findstr ":%%P " >nul 2>nul
  if errorlevel 1 (
    set PORT=%%P
    goto :found_port
  )
)
:found_port
if "%PORT%"=="" set PORT=8501
echo Usando puerto %PORT%...

REM Lanza Streamlit usando Python para no depender del PATH de streamlit
echo URL local: http://localhost:%PORT%
echo Si accedes desde otro equipo: http://<IP_DEL_HOST>:%PORT%
start "" http://localhost:%PORT%
python -m streamlit run main.py --server.address=0.0.0.0 --server.port=%PORT% --server.headless=false

echo.
echo ================================
echo   La app se ha cerrado.
echo ================================
pause
endlocal


