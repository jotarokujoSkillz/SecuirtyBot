from telegram.ext import CommandHandler, MessageHandler, filters
from commands.mute_unmute import mute_command, unmute_command
from commands.warn_ban import warn_command, ban_command, unwarn_command
from utils import welcome_command, handle_system_message
from antiflood.mediasystem import on_media_message
from callbacks.hasBoosted import unmute_callback_handler
from callbacks.premium_block import check_premium_message
import logging

# Configure the logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



# Modifica l'ordine degli handler per evitare conflitti
def setup_handlers(app):
    # 🟪 Callback inline (prima dei message handler)
    app.add_handler(unmute_callback_handler)
    
    # 🟦 Messaggi di sistema (es. potenziamenti)
    system_message_filter = filters.StatusUpdate.ALL
    logger.info("Registrazione dell'handler per i messaggi di sistema.")
    app.add_handler(MessageHandler(system_message_filter, handle_system_message), group=1)
    
    # 🟩 Premium check (intercetta tutti i messaggi tranne i comandi)
    premium_filter = filters.ALL & ~filters.StatusUpdate.ALL & ~filters.COMMAND
    app.add_handler(MessageHandler(premium_filter, check_premium_message), group=0)

    # Handler per i media (viene eseguito solo se il premium_block non blocca)
    media_filter = filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Sticker.ALL
    app.add_handler(MessageHandler(media_filter, on_media_message), group=2)
    
    # 🟦 Messaggi di benvenuto (primo in assoluto)
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_command))
        
    # 🟨 Comandi moderazione
    app.add_handler(CommandHandler("blocca", mute_command))
    app.add_handler(CommandHandler("libera", unmute_command))
    app.add_handler(CommandHandler("rwarn", warn_command))
    app.add_handler(CommandHandler("runwarn", unwarn_command))
    app.add_handler(CommandHandler("rban", ban_command))

