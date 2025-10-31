# A SEED — Cultivate peace of mind

**Project by:** Students from Nguyen Tat Thanh High School for the Gifted – Lao Cai Province  
**Message:** Nurturing positive seeds for yourself.

---

## 🇬🇧 OVERVIEW
**A SEED** is an empathetic AI chatbot designed to be a safe and private space for you to explore and understand your feelings. Our goal is to offer personalized, soothing conversations that adapt to you over time, acting as a supportive digital companion.

> ⚠️ **Disclaimer:** A SEED is a supportive companion, **not a substitute for professional mental-health care**. If you are in crisis, please contact local emergency services immediately.

### Key Features
- **Truly Personal & Adaptive AI**: The AI learns from your chat to provide relevant responses. The default model is `gpt-oss:120b-cloud`, enabling deep and empathetic conversations.
- **Accessible & Private**: Use our online version for instant access, or install the source code on your own machine for absolute privacy.
- **Dynamic & Soothing UI**: A clean, modern interface with a "Mood Orb" and color theme that dynamically changes based on the conversation's emotion. Includes Dark/Light modes.
- **Mood Statistics**: Track your emotional journey within a session with a beautiful chart, helping you gain insights into your feelings.

---

## 🚀 HOW TO ACCESS & USE

There are two ways to experience A SEED:

### Option 1: Online Access (Recommended)
This is the recommended method for most users. No installation is required.

**Simply open your browser and navigate to: [http://aseed.ddns.net/](http://aseed.ddns.net/)**

*(After accessing the link, please refer to the "App Usage Guide" section below.)*

### Option 2: Install from Source Code (For Developers)
This method is for users who wish to run the application on their own computer for absolute privacy or to customize the source code. If you choose this path, follow the detailed installation guide below.

---

## 📋 LOCAL INSTALLATION GUIDE

This section provides documentation for installing, configuring dependencies, and building the source code.

### 1. Prerequisites
Before you begin, ensure you have the following installed:
1.  **Python**: Version 3.10 or newer. Download from [python.org](https://python.org). **Important:** During installation, check the box that says "Add Python to PATH".
2.  **Ollama**: Download and install from [ollama.com](https://ollama.com). After installing, run the Ollama application once to start its background service.

### 2. Installation Steps

**Step 1: Get the Source Code**
- Download and extract the project's source code into a folder on your computer.

**Step 2: Install Python Dependencies**
- Open a terminal (Command Prompt, PowerShell, or Terminal) and navigate to the root directory of the project you just extracted.
- Run the following command to install all required libraries:
  ```bash
  pip install -r requirements.txt
  ```

**Step 3: Download the AI Model via Ollama**
- Make sure the Ollama application is running in the background.
- Open your terminal and run the following command to download the `gpt-oss:120b-cloud` model:
  ```bash
  ollama pull gpt-oss:120b-cloud
  ```
- **Note:** This is the default model configured in `main_server.py`. If you wish to use a different model, you must download it and change the `MODEL_NAME` variable in the `main_server.py` file.

**Step 4: Start the Server**
- After completing the steps above, run the following command in the terminal from the project's root directory:
  ```bash
  python main_server.py
  ```
- The server will start. Open your web browser and navigate to `http://127.0.0.1:8000` to use the application.

---

## 💡 APP USAGE GUIDE

This guide applies to both the online version and the locally installed version.

#### 1. Registration and Login
- **Create an Account:** On your first visit, you will need to create an account. Click on the **"Register"** tab, then enter your Display Name, a Username, and a Password.
- **Login:** After successfully creating an account, switch to the **"Login"** tab to sign in to the application.

#### 2. Starting a Conversation
- Once logged in, a welcome screen will appear. Click the **"Start"** button to enter the main chat interface.
- The AI will send a greeting message. You can reply to begin sharing your thoughts.

#### 3. Exploring the Main Features
- **➕ New Chat**: Start a completely new conversation.
- **History**: Review all of your past conversations.
- **📊 Mood Stats**: View a chart that visualizes the emotions detected by the AI during your current session.
- **🌙 Dark Mode / ☀️ Light Mode**: Switch between dark and light themes to suit your preference.
- **Logout**: Sign out of your account.


