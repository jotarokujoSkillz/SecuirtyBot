# /antiflood/mediasystem.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone, timedelta

# Dizionari per tracciare tempi media e nuovi utenti
last_media_time = {}
warned_users = {}
new_users_cooldown = {}  # user_id: join_time
immune_users = set()  # Set per tracciare gli utenti immuni

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def on_media_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = msg.from_user
    chat = msg.chat

    if chat.type not in ("group", "supergroup") or not user:
        return

    user_id = user.id

    # Controlla se l'utente è immune
    if user_id in immune_users:
        logger.info(f"Utente {user_id} immune al sistema di cooldown.")
        return

    if not (msg.photo or msg.video or msg.animation or msg.sticker):
        return

    now = datetime.now(timezone.utc)

    # Controllo blocco 30 minuti per nuovi utenti
    join_time = new_users_cooldown.get(user_id)
    if join_time:
        elapsed = (now - join_time).total_seconds()
        if elapsed < 1800:  # 30 minuti
            try:
                await msg.delete()
                logger.info(f"Media bloccato per nuovo utente {user_id}")
                
                if not warned_users.get(user_id, False):
                    await context.bot.send_message(
                        chat.id,
                        f"⏳ {user.first_name}, i nuovi utenti non possono inviare media per i primi 30 minuti!"
                    )
                    warned_users[user_id] = True
                return
            except Exception as e:
                logger.error(f"Errore cancellazione media: {e}")
                return

    # Sistema cooldown normale (1 minuto)
    last = last_media_time.get(user_id)
    if last and (now - last).total_seconds() < 60:
        try:
            await msg.delete()
            logger.info(f"Media eliminato per cooldown {user_id}")
        except Exception as e:
            logger.error(f"Errore cancellazione media: {e}")
        
        if not warned_users.get(user_id, False):
            await context.bot.send_message(
                chat.id,
                f"⚠️ {user.first_name}, puoi inviare media solo ogni 1 minuto!"
            )
            warned_users[user_id] = True
        return

    # Resetta i warning se tutto ok
    last_media_time[user_id] = now
    warned_users[user_id] = False
    logger.debug(f"Media permesso a {user_id}")
