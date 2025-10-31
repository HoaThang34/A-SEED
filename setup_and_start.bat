@echo off
setlocal EnableExtensions

REM =========================================================
REM  A SEED - First-Time Setup & Start (SILENT + OLLAMA AUTO)
REM =========================================================

REM ---- Configuration ----
if "%OLLAMA_HOST%"=="" set "OLLAMA_HOST=http://127.0.0.1:11434"
if "%MODEL_NAME%"==""  set "MODEL_NAME=gpt-oss:120b-cloud"
set "PY_MIN=3.10"
set "OLLAMA_WAIT_SEC=60"

REM ---- Logs ----
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1
set "PIP_LOG=%LOGDIR%\pip_install.log"
set "VENV_LOG=%LOGDIR%\venv_create.log"
set "MODEL_LOG=%LOGDIR%\ollama_pull.log"
set "SERVE_LOG=%LOGDIR%\ollama_serve.log"

echo ----------------------------------------------------------
echo  A SEED - Setup and Start
echo ----------------------------------------------------------
echo.

REM 1) Python
echo [1/7] Checking Python...
python --version >nul 2>nul
if errorlevel 1 (
  echo  ERROR: Python not found. Please install Python %PY_MIN%+ and add it to PATH.
  echo  Download: https://www.python.org/downloads/
  goto :end_pause
)
echo.

REM 2) Check Ollama installed
echo [2/7] Checking Ollama installation...
where ollama >nul 2>nul
if errorlevel 1 (
  echo  ERROR: Ollama is not installed.
  echo  Please install Ollama: https://ollama.com/download
  goto :end_pause
)
echo  Ollama CLI found.
echo.

REM 3) Ensure Ollama is running
echo [3/7] Ensuring Ollama service is running...
call :ensure_ollama_running
if errorlevel 1 (
  echo  ERROR: Could not start Ollama. Please start it manually and try again.
  goto :end_pause
)
echo  Ollama is online at %OLLAMA_HOST%.
echo.

REM 4) Create venv (silent)
if not exist ".venv\" (
  echo [4/7] Creating Python virtual environment...
  powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
    "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c python -m venv .venv ^>^> \"%VENV_LOG%\" 2^>^&1' -Wait"
  if errorlevel 1 (
    echo  ERROR: Failed to create virtual environment. See "%VENV_LOG%".
    goto :end_pause
  )
) else (
  echo [4/7] Virtual environment already exists.
)
echo.

REM 5) Install requirements (silent)
echo [5/7] Installing Python packages (running silently)...
call ".venv\Scripts\activate.bat" >nul 2>&1
if errorlevel 1 (
  echo  ERROR: Failed to activate virtual environment.
  goto :end_pause
)
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
  "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c pip install --no-input --disable-pip-version-check -r requirements.txt ^> \"%PIP_LOG%\" 2^>^&1' -Wait"
if errorlevel 1 (
  echo  ERROR: Failed to install dependencies. See "%PIP_LOG%".
  goto :end_pause
)
echo  Packages installed.
echo.

REM 6) (Optional) pull model silently
REM echo [6/7] Preparing AI model "%MODEL_NAME%" (running silently)...
REM powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
REM  "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c ollama pull %MODEL_NAME% ^> \"%MODEL_LOG%\" 2^>^&1' -Wait"

echo [6/7] Environment is ready.
echo.

REM 7) Start server
echo [7/7] Starting server...
set "PYTHONIOENCODING=utf-8"
set "MODEL_NAME=%MODEL_NAME%"
set "OLLAMA_HOST=%OLLAMA_HOST%"

start "" http://127.0.0.1:8000/
python main_server.py

echo.
echo Server stopped.
goto :end

:end_pause
echo.
echo Press any key to exit...
pause >nul
:end
endlocal
goto :eof

REM =======================
REM Helper: ensure Ollama
REM =======================
:ensure_ollama_running
REM 1) probe
call :ping_ollama
if not errorlevel 1 exit /b 0

REM 2) start silently
echo  Ollama is not reachable; attempting to start in background...
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
  "$p = Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c ollama serve ^>^> \"%SERVE_LOG%\" 2^>^&1' -PassThru; Start-Sleep -s 1"

REM 3) wait for ready
set /a "__wait=%OLLAMA_WAIT_SEC%"
:__ollama_wait_loop
call :ping_ollama
if not errorlevel 1 exit /b 0
set /a "__wait-=1"
if %__wait% LEQ 0 (
  echo  Timeout waiting for Ollama.
  exit /b 1
)
ping -n 2 127.0.0.1 >nul
goto :__ollama_wait_loop

:ping_ollama
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 '%OLLAMA_HOST%/api/tags' | Out-Null; exit 0 } catch { exit 1 }"
exit /b %ERRORLEVEL%
