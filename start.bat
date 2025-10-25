@echo off
echo [A SEED] Starting setup for Ollama...

:: ==========================================================
:: CONFIGURE YOUR OLLAMA MODEL HERE
:: "gpt-oss:120b-cloud" is a good starting point.
:: Make sure you have pulled this model with `ollama pull <model_name>`
:: ==========================================================
set OLLAMA_HOST=http://127.0.0.1:11434
set MODEL_NAME=gpt-oss:120b-cloud

:: Check for Python
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found. Please install Python 3.10+ and add it to your PATH.
    pause
    exit /b 1
)

:: Create/activate virtual environment and install dependencies
if not exist .venv (
    echo [A SEED] Creating virtual environment...
    python -m venv .venv
)
echo [A SEED] Activating environment and installing libraries...
call .venv\Scripts\activate.bat
pip install -r requirements.txt

:: Set environment variable for encoding to prevent errors with special characters
set PYTHONIOENCODING=utf-8

:: Automatically open the browser
echo [A SEED] Opening browser...
start http://127.0.0.1:8000/

:: Run the Flask server
echo [A SEED] Starting server. You can close this window to stop it.
echo ==========================================================
python main_server.py

pause