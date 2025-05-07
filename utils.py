import logging
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from io import BytesIO
from antiflood.mediasystem import last_media_time, warned_users, new_users_cooldown
from pyrogram import Client
from pyrogram.raw.functions.contacts import ResolveUsername
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

API_ID = config.API_ID
API_HASH = config.API_HASH
BOT_TOKEN = config.BOT_TOKEN

# Configura il tuo client Pyrogram
app = Client("RottenShielBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

logger = logging.getLogger(__name__)

# Stato globale
verified_boosters = set()     # utenti premium che hanno boostato
recently_muted = {}           # user_id → datetime dell’ultimo mute premium
username_map = {}             # mappa username → user_id

# Path dell’immagine di benvenuto
WELCOME_IMAGE = "image.jpg"

async def send_temp_message(chat_id, bot, text, delay=10):
    """Invia un messaggio temporaneo che viene cancellato automaticamente dopo `delay` secondi."""
    message = await bot.send_message(chat_id=chat_id, text=text)
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

async def send_private_or_group_message(issuer_id, chat_id, bot, text, delay=10):
    """
    Invia un messaggio in privato se l'utente ha avviato il bot, altrimenti nel gruppo con cancellazione automatica.
    Restituisce:
        - "private" se il messaggio è stato inviato in privato.
        - "group" se il messaggio è stato inviato nel gruppo.
    """
    try:
        # Prova a inviare il messaggio in privato
        await bot.send_message(chat_id=issuer_id, text=text)
        return "private"
    except:
        # Se fallisce, invia nel gruppo e cancella dopo `delay` secondi
        await send_temp_message(chat_id=chat_id, bot=bot, text=text, delay=delay)
        return "group"
    
async def welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Esecuzione del comando di benvenuto.")
    new_members = update.message.new_chat_members
    if not new_members:
        return

    for user in new_members:
        try:
            new_users_cooldown[user.id] = datetime.now(timezone.utc)
            
            with open(WELCOME_IMAGE, "rb") as image:
                caption = (
                    f"👋 Benvenuto {user.mention_html()} su <b>𝙍𝙊𝙏𝙏𝙀𝙉 𝙂𝙍𝘼𝙈</b>\n\n"
                    "⚠️ Per i <u>primi 30 minuti</u> non potrai inviare:\n"
                    "<blockquote>"
                    "• Foto\n"
                    "• Video\n"
                    "• GIF\n"
                    "• Stickers\n"
                    "</blockquote>\n"
                    "<i>Dopo questo periodo avrai un limite di 1 media al minuto.</i>"
                )
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=InputFile(image),
                    caption=caption,
                    parse_mode="HTML"
                )
                logger.info(f"Registrato nuovo utente: {user.id}")
        except Exception as e:
            logger.error(f"Errore welcome: {str(e)}")

# ——— Funzione di supporto per /mute e /unmute - /warn e /ban ————————————
async def resolve_username_to_user_id(username: str):
    async with app:
        try:
            logger.info(f"Risoluzione dello username: {username}")
            result = await app.invoke(ResolveUsername(username=username))
            if result.users:
                logger.info(f"Utente trovato: {result.users[0].id}")
                return result.users[0].id
            else:
                logger.warning(f"Nessun utente trovato per username: {username}")
                return None
        except Exception as e:
            if "USERNAME_INVALID" in str(e):
                logger.error(f"Errore: Username '{username}' non valido.")
            else:
                logger.error(f"Errore durante la risoluzione dello username: {str(e)}")
            return None

async def resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if message.reply_to_message:
        return message.reply_to_message.from_user

    args = context.args
    if args:
        if args[0].isdigit():
            try:
                user = await context.bot.get_chat(int(args[0]))
                return user
            except Exception as e:
                await send_private_or_group_message(
                    issuer_id=update.effective_user.id,
                    chat_id=update.effective_chat.id,
                    bot=context.bot,
                    text="Impossibile trovare l'utente da ID."
                )
                return None
        else:
            # Fallback: risolvi lo username
            username = args[0].lstrip("@")  # Rimuove il simbolo '@' se presente
            user_id = await resolve_username_to_user_id(username)
            if user_id:
                try:
                    user = await context.bot.get_chat(user_id)
                    return user
                except Exception as e:
                    await send_private_or_group_message(
                        issuer_id=update.effective_user.id,
                        chat_id=update.effective_chat.id,
                        bot=context.bot,
                        text="Impossibile trovare l'utente dallo username."
                    )
                    return None
    return None

async def handle_system_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Intercetta i messaggi di sistema e logga il contenuto per verificare se vengono rilevati correttamente.
    """
    message = update.effective_message
    logger.info("Intercettato un messaggio di sistema.")
    
    if not message:
        logger.warning("Nessun messaggio trovato nell'update.")
        return

    logger.debug(f"Contenuto del messaggio: {message}")
    if message.text:
        logger.info(f"Testo del messaggio di sistema: {message.text}")
    else:
        logger.info("Il messaggio di sistema non contiene testo.")

    # Logghiamo i dettagli del messaggio per capire il tipo di evento
    if message.left_chat_member:
        logger.info(f"Utente rimosso: {message.left_chat_member.id} ({message.left_chat_member.username})")
    if message.new_chat_members:
        logger.info(f"Nuovi membri aggiunti: {[user.id for user in message.new_chat_members]}")
    if message.group_chat_created:
        logger.info("Il gruppo è stato creato.")
    if message.supergroup_chat_created:
        logger.info("Il supergruppo è stato creato.")
    if message.migrate_to_chat_id:
        logger.info(f"Il gruppo è stato migrato a: {message.migrate_to_chat_id}")
    if message.migrate_from_chat_id:
        logger.info(f"Il gruppo è stato migrato da: {message.migrate_from_chat_id}")
    if "ha potenziato il gruppo" in (message.text or "").lower():
        try:
            user = message.from_user
            if user:
                logger.info(f"Utente che ha potenziato: {user.id} ({user.username})")
                thank_you_message = (
                    f"🎉 Grazie {user.mention_html()} per aver potenziato il gruppo! "
                    "Il tuo supporto è molto apprezzato! 💪"
                )
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=thank_you_message,
                    parse_mode=ParseMode.HTML
                )
                logger.info(f"Messaggio di ringraziamento inviato a {user.id}")
            else:
                logger.warning("Impossibile determinare l'utente dal messaggio.")
        except Exception as e:
            logger.error(f"Errore nell'invio del messaggio di ringraziamento: {str(e)}")

