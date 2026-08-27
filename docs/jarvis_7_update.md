# JARVIS MARK VII - UPGRADE BLUEPRINT

This blueprint has been restructured to prioritize UX, plumbing, and strict security guardrails before deploying dangerous autonomous or remote-access capabilities.

## Phase 1: UX & Foundation
### 1. Dual-Modal Interface (Voice + Text Chat)
- **Concept:** A sleek manual override text box added to the web HUD. The core backend microphone loop will simultaneously listen for incoming WebSocket text queues, allowing seamless switching between voice and silent typing.

### 2. Multi-Modal File Sharing (Images & PDFs)
- **Concept:** A drag-and-drop file upload zone in the HUD. Jarvis will use the Gemini Vision model to instantly read PDFs or visually analyze images sent to him.

### 3. Universal Dynamic Locator (App & Folder Execution)
- **Concept:** Hardcoded scripts replaced with a dynamic Windows API search hook (`Get-StartApps`). 
- **Safety Upgrade:** To prevent massive latency from recursive drive scanning, Jarvis will build a lightweight, cached JSON map of all installed `.exe` files on startup, updating it silently once a day.

### 4. Long-Term Vector Memory (RAG)
- **Concept:** A permanent Vector Database (ChromaDB/FAISS) to remember facts and ideas.
- **Safety Upgrade 1 (Cost):** A lightweight *secondary* LLM call will be used exclusively for memory retrieval to prevent context bloat.
- **Safety Upgrade 2 (Sanitation):** Strict data sanitization before ingestion to ensure scraped web content cannot perform prompt injections into Jarvis's long-term memory.

### 5. Automated Neural Hot-Swapping (Infinite Rate Limits)
- **Concept:** If a `429 Rate Limit` error is thrown, Jarvis silently catches it and hot-swaps to the next available backup key without interrupting the user.

## Phase 2: Autonomy & Agency
### 6. Action Confirmation Gate (Architectural Choke Point)
- **Concept:** A mandatory, hardcoded security layer injected directly into the tool dispatcher *before* any autonomous features are built.
- **Rules:** Any "destructive" or "one-way" tool will be physically blocked by the system until explicit secondary authorization is given. 
- **Covered Actions:** `format_drive`, `power_options`, making financial purchases via Playwright, and **sending emails/calendar invites to external recipients**.
- **Remote 2FA:** If a dangerous action is triggered remotely via Telegram, the confirmation *cannot* happen over Telegram. The user must authorize it locally on the host machine (via Voice or HUD Text) to prevent compromised-account attacks.

### 7. Autonomous ReAct Loop (Agentic Cognitive Engine)
- **Concept:** Jarvis is upgraded from a reactive chatbot to a fully autonomous Agent, wrapping his `chat()` engine in a cognitive `while` loop.
- **Safety Upgrade:** A strict `max_iterations` cap (e.g., 5 loops) will be enforced to prevent quota burn and infinite failure loops.

### 8. Dual-Mode Web Surfing (Background & Live Control)
- **Concept:** Combines a silent background scraper for fast data retrieval with Playwright for physical control of the active visible browser.

### 9. Executive Email & Calendar Authority
- **Concept:** Jarvis connects to Gmail/Google Calendar to draft, read, and manage communications.

## 10. Instagram Intelligence Integration (Playwright Extension)
- **Concept:** Utilizing the Dual-Mode Web Surfing engine, Jarvis will be able to navigate to Instagram pages using your active session. He will extract bios, follower counts, and recent captions, cross-reference them with background web searches, and synthesize analytical comparisons—all while strictly adhering to read-only safety limits.
- **Cost:** Free.

## 11. Telegram Remote Control (Worldwide Access)
- **Concept:** A private Telegram bot allowing you to text commands to your laptop from anywhere in the world.
- **Safety Upgrade:** Strict UID allowlisting will be hardcoded (`update.effective_user.id`). Jarvis will completely ignore any messages from unauthorized users.

## Phase 3: Visuals
### 11. Advanced Cybernetic HUD Redesign (Visual Overhaul)
- **Concept:** The UI will be completely rebuilt to match the reference image: highly detailed concentric radar rings, structural data flow lines, and signal quality bars using advanced CSS/HTML canvas engineering.

*Note: Native EXE Deployment and IoT integration have been excluded from this build as per the user's request to maintain a fast debug loop.*

**STATUS: WAITING FOR AUTHORIZATION**
*(Do not execute until user commands: "update jarvis to 7")*
