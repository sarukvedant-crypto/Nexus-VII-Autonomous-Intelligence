"""
J.A.R.V.I.S. Telegram Remote Control
=====================================
Allows remote command execution via Telegram with strict UID allowlisting.
Only the configured Telegram user ID can interact with the bot.
"""
import os
import threading
import logging
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

load_dotenv()
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALLOWED_UID = os.getenv("TELEGRAM_ALLOWED_UID", "")

def start_telegram_bot(ai_instance):
    """Starts the Telegram bot in a background thread.
    
    Args:
        ai_instance: A UniversalAI instance to process commands.
    """
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or TELEGRAM_BOT_TOKEN == "your-telegram-bot-token-here":
        logger.warning("Telegram bot token not configured. Skipping Telegram integration.")
        return None

    try:
        from telegram import Update
        from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
    except ImportError:
        logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        return None

    allowed_uids = set()
    if TELEGRAM_ALLOWED_UID:
        for uid in TELEGRAM_ALLOWED_UID.split(","):
            uid = uid.strip()
            if uid.isdigit():
                allowed_uids.add(int(uid))

    def is_authorized(user_id: int) -> bool:
        """Check if the user is in the allowlist."""
        if not allowed_uids:
            return False  # No UIDs configured = deny all
        return user_id in allowed_uids

    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update.effective_user.id):
            return  # Silently drop unauthorized users
        await update.message.reply_text(
            "J.A.R.V.I.S. Telegram uplink established, Sir.\n"
            "Send me any command and I'll execute it remotely."
        )

    async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update.effective_user.id):
            return
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        batt = psutil.sensors_battery()
        power = f"{batt.percent}%" if batt else "AC Power"
        await update.message.reply_text(
            f"System Status:\nCPU: {cpu}%\nRAM: {ram}%\nPower: {power}"
        )

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update.effective_user.id):
            return  # Silently drop unauthorized users
        
        user_text = update.message.caption or update.message.text or "What is in this image?"
        
        media_path = None
        if update.message.photo:
            try:
                # Get the highest resolution photo
                photo_file = await update.message.photo[-1].get_file()
                
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(PROJECT_ROOT, "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                
                # Download to a temporary file
                media_path = os.path.join(upload_dir, f"telegram_{update.message.message_id}.jpg")
                await photo_file.download_to_drive(custom_path=media_path)
                await update.message.reply_text("Image received. Analyzing...")
            except Exception as e:
                await update.message.reply_text(f"Error downloading image: {e}")
                return
        elif update.message.document:
            try:
                doc_file = await update.message.document.get_file()
                file_name = update.message.document.file_name
                ext = os.path.splitext(file_name)[1].lower() if file_name else ""
                
                upload_dir = os.path.join(PROJECT_ROOT, "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                
                media_path = os.path.join(upload_dir, f"telegram_{update.message.message_id}{ext}")
                await doc_file.download_to_drive(custom_path=media_path)
                
                if ext == ".pdf":
                    await update.message.reply_text(f"PDF received: {file_name}. Reading...")
                    if user_text == "What is in this image?":
                        user_text = f"Please read this PDF and summarize it."
                else:
                    await update.message.reply_text(f"Document received: {file_name}.")
            except Exception as e:
                await update.message.reply_text(f"Error downloading document: {e}")
                return

        try:
            # Process through the AI engine
            response = ai_instance.chat(user_text, media_path=media_path)
            
            import re
            media_matches = re.findall(r'\[SEND_MEDIA:\s*(.+?)\]', response)
            response = re.sub(r'\[SEND_MEDIA:\s*(.+?)\]', '', response).strip()
            
            if response:
                # Telegram has a 4096 char limit per message
                if len(response) > 4000:
                    # Split into chunks
                    for i in range(0, len(response), 4000):
                        await update.message.reply_text(response[i:i+4000])
                else:
                    await update.message.reply_text(response)
                    
            for m_path in media_matches:
                m_path = m_path.strip()
                if os.path.exists(m_path):
                    ext = m_path.lower().split('.')[-1]
                    if ext in ['png', 'jpg', 'jpeg', 'webp']:
                        await update.message.reply_photo(photo=open(m_path, 'rb'))
                    elif ext in ['mp4', 'avi', 'mov']:
                        await update.message.reply_video(video=open(m_path, 'rb'))
                    else:
                        await update.message.reply_document(document=open(m_path, 'rb'))
                else:
                    await update.message.reply_text(f"[System: Media attachment failed. File not found: {m_path}]")
        except Exception as e:
            await update.message.reply_text(f"Error processing command: {e}")

    def _run_bot():
        """Runs the Telegram bot in its own asyncio event loop."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("status", cmd_status))
        app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, handle_message))
        
        logger.info("Telegram bot started successfully.")
        loop.run_until_complete(app.run_polling(drop_pending_updates=True))

    bot_thread = threading.Thread(target=_run_bot, daemon=True)
    bot_thread.start()
    return bot_thread
