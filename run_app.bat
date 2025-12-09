@echo off
setlocal

set APP_DIR=%~dp0

where python >nul 2>nul
if errorlevel 1 (
  echo Necesitas instalar Python 3.11+ y marcar "Add to PATH".
  pause
  exit /b 1
)

cd /d "%APP_DIR%"

if not exist ".venv" (
  python -m venv .venv
)

call .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist "data" mkdir data
if not exist "data\saves" mkdir data\saves

rem Buscar puerto libre empezando en 8501 hasta 8510
set PORT=
for /L %%P in (8501,1,8510) do (
  rem Revisar si hay algo escuchando en el puerto %%P
  netstat -ano | findstr ":%%P " >nul 2>nul
  if errorlevel 1 (
    set PORT=%%P
    goto :found_port
  )
)
:found_port
if "%PORT%"=="" set PORT=8501

echo Usando puerto %PORT%...
echo URL local: http://localhost:%PORT%
echo Si accedes desde otro equipo: http://<IP_DEL_HOST>:%PORT%
start "" http://localhost:%PORT%
streamlit run main.py --server.address=0.0.0.0 --server.port=%PORT% --server.headless=true

set EXITCODE=%ERRORLEVEL%
if not %EXITCODE%==0 (
  echo.
  echo La app se cerro con codigo %EXITCODE%.
  echo Revisa si ya hay otra instancia usando el puerto %PORT%.
  pause
)

endlocal


