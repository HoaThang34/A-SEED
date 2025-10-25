@echo off
setlocal

echo ==========================================================
echo  A SEED - First-Time Setup & Start
echo ==========================================================
echo.
echo This script will check for prerequisites, download the AI model,
echo set up the Python environment, and start the server.
echo.

:: === Step 1: Check for prerequisites (Python & Ollama) ===
echo [1/5] Checking for Python and Ollama...

python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found on your system PATH.
    echo Please download and install Python 3.10+ from python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

ollama --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Ollama is not found on your system PATH.
    echo Please download and install Ollama from ollama.com
    echo After installation, please run Ollama once to start its service.
    pause
    exit /b 1
)

echo [OK] Python and Ollama found.
echo.

:: === Step 2: Download the AI Model ===
echo [2/5] Checking for the required AI model...
set "MODEL_NAME=gpt-oss:120b-cloud"
ollama list | findstr /C:"%MODEL_NAME%" >nul
if %errorlevel% neq 0 (
    echo Model '%MODEL_NAME%' not found. Starting download...
    ollama pull %MODEL_NAME%
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to download the AI model. Please check your internet connection and try again.
        pause
        exit /b 1
    )
    echo [OK] Model downloaded successfully.
) else (
    echo [OK] Model '%MODEL_NAME%' is already installed.
)
echo.

:: === Step 3: Set up Python Environment ===
echo [3/5] Setting up Python environment...
if not exist .venv (
    echo      - Creating virtual environment...
    python -m venv .venv
)
echo      - Activating environment and installing libraries...
call .venv\Scripts\activate.bat
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python libraries. Please check your internet connection.
    pause
    exit /b 1
)
echo [OK] Python environment is ready.
echo.

:: === Step 4: Ensure Ollama service is running ===
echo [4/5] Checking if Ollama service is running...
ollama ps >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Ollama service might not be running.
    echo Please make sure the Ollama application is running in your system tray.
    echo The application might not work if the service is stopped.
    echo Press any key to continue anyway...
    pause
) else (
    echo [OK] Ollama service is active.
)
echo.

:: === Step 5: Start the A SEED Server ===
echo [5/5] Starting the A SEED server...
echo.

set OLLAMA_HOST=http://127.0.0.1:11434
set MODEL_NAME=%MODEL_NAME%
set PYTHONIOENCODING=utf-8

start http://127.0.0.1:8000/
python main_server.py

echo.
echo Server has been stopped.
pause