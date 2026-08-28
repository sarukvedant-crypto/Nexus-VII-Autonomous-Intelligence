# Nexus VII â€” Autonomous Intelligence

<div align="center">

**A J.A.R.V.I.S.-inspired autonomous AI assistant with voice control, Telegram integration, proactive reminders, web form automation, screen analysis, and neural hot-swapping across multiple AI providers.**

Built with Python Â· FastAPI Â· WebSockets Â· Google Gemini Â· NVIDIA Â· Mistral AI

<br>
<img src="https://img.shields.io/github/license/vedant-saruk/Nexus-VII-Autonomous-Intelligence?style=flat-square" alt="License">
<img src="https://img.shields.io/github/stars/vedant-saruk/Nexus-VII-Autonomous-Intelligence?style=flat-square" alt="Stars">
<img src="https://img.shields.io/github/forks/vedant-saruk/Nexus-VII-Autonomous-Intelligence?style=flat-square" alt="Forks">
<img src="https://img.shields.io/github/issues/vedant-saruk/Nexus-VII-Autonomous-Intelligence?style=flat-square" alt="Issues">
<br>

</div>

---

## âœ¨ Features

| Feature | Description |
|---------|-------------|
| **ðŸŽ™ï¸ Voice Control** | Speak to your assistant using real-time speech recognition and TTS. |
| **ðŸ’¬ Telegram Bot** | Remote control and notifications via a personal Telegram bot. |
| **ðŸ§  Proactive Engine** | Autonomous background AI that monitors your goals and sends nudges. |
| **ðŸ“ Web Form Automation** | AI-powered Google Forms and web form filling via Playwright. |
| **ðŸ‘ï¸ Screen Analysis** | OCR and Gemini-powered vision to understand what's on your screen. |
| **âš¡ Neural Hot-Swapping** | Seamless automatic failover across multiple AI providers when rate limits hit. |
| **ðŸ“… Google Calendar** | Check and create calendar events via the Google Calendar API. |
| **ðŸ“¥ Google Drive** | Download files and entire folders from Google Drive shared links. |
| **ðŸ§  Vector Memory** | Persistent long-term memory with semantic recall (RAG). |
| **ðŸ“„ PDF Generation** | Beautiful, themed PDF creation with Playwright rendering. |
| **ðŸŽ¯ Skills System** | Extensible skill/plugin system to teach your AI new behaviors. |
| **ðŸŽµ Spotify Automation** | Headless browser track searching and playback without needing API keys. |
| **ðŸŽ¬ Video Editing** | Automate DaVinci Resolve via scripts to import clips and organize media. |
| **ðŸš€ Smart App Locator** | Dynamically finds and launches Windows apps using deep registry scanning. |

---

## ðŸ“ Directory Structure

```
Nexus-VII-Autonomous-Intelligence/
â”œâ”€â”€ api/             # External service integrations (Telegram bot, reminders)
â”œâ”€â”€ auth/            # Google OAuth credentials (you provide these)
â”œâ”€â”€ core/            # Main AI engine, server, vector memory, proactive engine
â”œâ”€â”€ data/            # Local databases, caches, memory, and goals
â”œâ”€â”€ docs/            # Project documentation and ideas
â”œâ”€â”€ modules/         # Specialized modules (OCR, Calendar, Drive, PDF, App Locator)
â”œâ”€â”€ scripts/         # Utility scripts (Syllabus generator, file organizer)
â”œâ”€â”€ skills/          # AI behavior rules and skill files (.md/.txt)
â”œâ”€â”€ static/          # Web UI (HTML, CSS, JS, particles)
â”œâ”€â”€ temp/            # Temporary processing files
â”œâ”€â”€ tests/           # Test scripts
â”œâ”€â”€ .env.example     # Environment variable template (copy to .env)
â”œâ”€â”€ launch_jarvis.bat# One-click launcher for Windows
â””â”€â”€ requirements.txt # Python dependencies
```

---

## ðŸš€ Setup Instructions

### Prerequisites

- **Python 3.10+** â€” [Download](https://www.python.org/downloads/)
- **Windows 10/11** â€” This project uses Windows-specific APIs (registry, PowerShell, etc.)
- **Git** â€” [Download](https://git-scm.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/vedant-saruk/Nexus-VII-Autonomous-Intelligence.git
cd Nexus-VII-Autonomous-Intelligence
```

### 2. Create & Activate a Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install External Tools

Some features require additional system-level installations:

| Tool | Required For | Install Command |
|------|-------------|-----------------|
| **Playwright** | PDF generation, web automation | `playwright install` |
| **Tesseract OCR** | Image text extraction | [Download Installer](https://github.com/UB-Mannheim/tesseract/wiki) |

### 5. Configure Environment Variables

```bash
copy .env.example .env
```

Open `.env` in a text editor and fill in your API keys:

#### ðŸ”‘ Required (at minimum one)

| Variable | Where to Get It |
|----------|----------------|
| `AI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) (free) |
| `AI_BASE_URL` | Pre-filled for Gemini. Change if using Groq/Ollama. |
| `AI_MODEL` | Pre-filled. Change if using a different model. |

#### ðŸ”‘ Optional Integrations

| Variable | Where to Get It |
|----------|----------------|
| `GEMINI_API_KEY` | Same as above, used for vision & memory features |
| `NVIDIA_API_KEY` | [NVIDIA Build](https://build.nvidia.com/) |
| `BACKUP_*` keys | Additional API keys for hot-swap failover |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | [Google App Passwords](https://myaccount.google.com/apppasswords) (requires 2FA) |
| `TELEGRAM_BOT_TOKEN` | Create a bot via [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_ALLOWED_UID` | Get your ID via [@userinfobot](https://t.me/userinfobot) on Telegram |

### 6. Set Up Google Calendar & Drive (Optional)

To enable Google Calendar and Drive features:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Enable the **Google Calendar API** and **Google Drive API**.
4. Go to **Credentials** â†’ **Create Credentials** â†’ **OAuth 2.0 Client ID**.
5. Download the JSON file and save it as `auth/credentials.json`.
6. On first use, a browser window will open for you to authorize access. The resulting `auth/token.json` will be created automatically.

### 7. Launch

**Option A: One-click (recommended)**
```bash
launch_jarvis.bat
```

**Option B: Manual**
```bash
venv\Scripts\activate
python core/server.py
```

Then open **http://localhost:8000** in your browser.

---

## ðŸ–¥ï¸ Web UI

The HUD (Heads-Up Display) runs in your browser and provides:

- Real-time chat with the AI (text + voice)
- System telemetry (CPU, RAM, power, storage)
- Memory management (add/view/edit persistent memories)
- Settings panel (change AI provider, keys, voice, integrations)
- Skills center (import, upload, and manage AI skills)
- File upload and image analysis

---

## ðŸ¤– Telegram Setup

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to create your bot.
3. Copy the bot token and paste it into `TELEGRAM_BOT_TOKEN` in your `.env`.
4. Message [@userinfobot](https://t.me/userinfobot) to get your Telegram user ID.
5. Paste your ID into `TELEGRAM_ALLOWED_UID` in your `.env`.
6. Restart the server. Your bot will now be active!

---

## âš™ï¸ Supported AI Providers

| Provider | Base URL | Models |
|----------|----------|--------|
| **Google Gemini** | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-3.5-flash-lite`, `gemini-3.5-flash` |
| **NVIDIA** | `https://integrate.api.nvidia.com/v1` | `meta/llama-3.3-70b-instruct`, `nvidia/nemotron-3-super-120b-a12b` |
| **Mistral AI** | `https://api.mistral.ai/v1` | `mistral-small-latest` |
| **Groq** | `https://api.groq.com/openai/v1` | `llama-3.1-8b-instant` |
| **Ollama** (local) | `http://localhost:11434/v1` | Any locally running model |

The neural hot-swapping system automatically rotates through your configured backup providers when rate limits are encountered.

---

## ðŸ“œ Scripts

Utility scripts in the `scripts/` folder:

| Script | Description |
|--------|-------------|
| `generate_syllabus.py` | Generates a beautifully formatted PDF syllabus from course data. |
| `import_clips_to_resolve.py` | Imports MP4 clips into DaVinci Resolve via API or GUI automation. |
| `organize_files.py` | Organizes files in a folder by name-based numeric sorting. |

---

## ðŸ›¡ï¸ Security Notes

- Your `.env` file is **gitignored** and will never be committed.
- `auth/credentials.json` and `auth/token.json` are **gitignored**.
- Personal data files (`memory_db.json`, `goals.json`, `memory.txt`, `app_cache.json`) are **gitignored**.
- The Telegram bot only responds to the user ID specified in `TELEGRAM_ALLOWED_UID`.

---

## ðŸ“ License

Distributed under the MIT License. See `LICENSE` for more information.

---

## ðŸ™ Acknowledgments

Inspired by J.A.R.V.I.S. from the Marvel Cinematic Universe.
Built with Google Gemini, NVIDIA NIM, Mistral AI, FastAPI, and Playwright.

