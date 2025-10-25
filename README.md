# A SEED — Aware. Soothe. Embrace. Evolve. Deliver.

**Project by:** Students from Nguyen Tat Thanh High School for the Gifted – Lao Cai Province  
**Message:** Nurturing positive seeds for yourself.

---

## 🇬🇧 OVERVIEW
**A SEED** is an empathetic chatbot that runs **fully on your local machine**, designed to be a safe space for exploring and understanding your feelings. It offers personalized, soothing conversations that adapt to you over time.

> ⚠️ **Disclaimer:** A SEED is a supportive companion, **not a substitute for professional mental-health care**. If you are in crisis, please contact local emergency services immediately.

### Key Features
- **Truly Personal & Adaptive AI**: The AI learns from your chat to provide relevant responses, remembers your hobbies, and can adapt its communication style with your consent.
- **100% Local & Private**: Runs entirely on your machine using Flask and Ollama. Your conversations are tied to your private user account.
- **Dynamic & Soothing UI**: A clean, modern interface with a "Mood Orb" and color theme that dynamically changes based on the conversation's emotion. Includes Dark/Light modes.
- **Mood Statistics**: Track your emotional journey within a session with a beautiful chart.
- **Admin Dashboard**: A built-in admin panel to monitor server health and performance.

### Prerequisites
Before you begin, ensure you have these installed:
1.  **Python**: Version 3.10 or newer. Download from [python.org](https://python.org). **Important:** During installation, check the box that says "Add Python to PATH".
2.  **Ollama**: Download and install from [ollama.com](https://ollama.com). After installing, run the Ollama application once to start its background service.

---

## 🚀 One-Click Setup (For a New Machine)
For the very first time on a new computer, use this script. It will handle everything automatically.

1.  **Run `setup_and_start.bat`**
    - Double-click the `setup_and_start.bat` file.
    - The script will:
        - Check if you have Python and Ollama.
        - Automatically download the required AI model (`qwen2.5:7b-instruct`).
        - Set up the Python environment and install all libraries.
        - Start the A SEED server.
        - Open the application in your web browser.

## 🏃 Daily Use (After First-Time Setup)
Once everything is set up, you can use the simpler `start.bat` file for daily use.

1.  **Ensure Ollama is running**: Make sure the Ollama icon is in your system tray.
2.  **Run `start.bat`**: Double-click this file to quickly start the server and open the app.

---

## 🧠 Customizing the AI
You can edit the AI's core personality by modifying `training/a_seed_prompt.txt`. The server will automatically use the new instructions.