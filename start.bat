@echo off
setlocal EnableExtensions

REM ===============================================
REM  A SEED - Start (SILENT + OLLAMA AUTO)
REM ===============================================

REM ---- Configuration ----
if "%OLLAMA_HOST%"=="" set "OLLAMA_HOST=http://127.0.0.1:11434"
if "%MODEL_NAME%"==""  set "MODEL_NAME=gpt-oss:120b-cloud"
set "OLLAMA_WAIT_SEC=60"

REM ---- Logs ----
set "LOGDIR=%~dp0logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%" >nul 2>&1
set "PIP_LOG=%LOGDIR%\pip_install.log"
set "VENV_LOG=%LOGDIR%\venv_create.log"
set "MODEL_LOG=%LOGDIR%\ollama_pull.log"
set "SERVE_LOG=%LOGDIR%\ollama_serve.log"

echo -----------------------------------------------
echo  A SEED - Start
echo -----------------------------------------------
echo.

REM 1) Python
echo [1/5] Checking Python...
python --version >nul 2>nul
if errorlevel 1 (
  echo  ERROR: Python not found. Install Python 3.10+ and add it to PATH.
  goto :end_pause
)
echo.

REM 2) Ollama present?
echo [2/5] Checking Ollama installation...
where ollama >nul 2>nul
if errorlevel 1 (
  echo  ERROR: Ollama is not installed.
  echo  Please install Ollama: https://ollama.com/download
  goto :end_pause
)
echo  Ollama CLI found.
echo.

REM 3) Ensure Ollama is running
echo [3/5] Ensuring Ollama service is running...
call :ensure_ollama_running
if errorlevel 1 (
  echo  ERROR: Could not start Ollama. Please start it manually and try again.
  goto :end_pause
)
echo  Ollama is online at %OLLAMA_HOST%.
echo.

REM 4) venv + requirements (silent)
if not exist ".venv\" (
  echo [4/5] Creating virtual environment...
  powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
    "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c python -m venv .venv ^>^> \"%VENV_LOG%\" 2^>^&1' -Wait"
  if errorlevel 1 (
    echo  ERROR: Failed to create virtual environment. See "%VENV_LOG%".
    goto :end_pause
  )
) else (
  echo [4/5] Virtual environment already exists.
)
call ".venv\Scripts\activate.bat" >nul 2>&1
if errorlevel 1 (
  echo  ERROR: Failed to activate virtual environment.
  goto :end_pause
)

echo  Installing dependencies (running silently)...
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
  "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c pip install --no-input --disable-pip-version-check -r requirements.txt ^> \"%PIP_LOG%\" 2^>^&1' -Wait"
if errorlevel 1 (
  echo  ERROR: Failed to install dependencies. See "%PIP_LOG%".
  goto :end_pause
)
echo  Dependencies OK.
echo.

REM (Optional) pull model silently
REM echo Preparing model "%MODEL_NAME%" (silent)...
REM powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
REM  "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c ollama pull %MODEL_NAME% ^> \"%MODEL_LOG%\" 2^>^&1' -Wait"

REM 5) Launch server
echo [5/5] Launching server...
set "PYTHONIOENCODING=utf-8"
set "MODEL_NAME=%MODEL_NAME%"
set "OLLAMA_HOST=%OLLAMA_HOST%"

start "" http://127.0.0.1:8000/
python main_server.py

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
call :ping_ollama
if not errorlevel 1 exit /b 0

echo  Ollama is not reachable; attempting to start in background...
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
  "$p = Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c ollama serve ^>^> \"%SERVE_LOG%\" 2^>^&1' -PassThru; Start-Sleep -s 1"

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
