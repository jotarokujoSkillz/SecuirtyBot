from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from database.db_manager import get_db_session, Settings
import logging

logger = logging.getLogger(__name__)

async def premium_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    try:
        chat_member = await context.bot.get_chat_member(chat.id, user.id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("⚠️ Solo gli amministratori possono eseguire questo comando.")
            return

        with get_db_session() as session:
            setting = session.query(Settings).filter(Settings.key == "premium_check").first()
            if setting and setting.value == "enabled":
                await update.message.reply_text("⚠️ Il controllo premium è già attivo.")
                return

            if not setting:
                setting = Settings(key="premium_check", value="enabled")
                session.add(setting)
            else:
                setting.value = "enabled"
            session.commit()

        await update.message.reply_text("✅ Controllo premium attivato con successo.")

    except BadRequest as e:
        logger.error(f"Errore API: {str(e)}")
    except Exception as e:
        logger.error(f"Errore generale: {str(e)}", exc_info=True)

async def premium_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    try:
        chat_member = await context.bot.get_chat_member(chat.id, user.id)
        if chat_member.status not in ['creator', 'administrator']:
            await update.message.reply_text("⚠️ Solo gli amministratori possono eseguire questo comando.")
            return

        with get_db_session() as session:
            setting = session.query(Settings).filter(Settings.key == "premium_check").first()
            if setting and setting.value == "disabled":
                await update.message.reply_text("⚠️ Il controllo premium è già disattivato.")
                return

            if not setting:
                setting = Settings(key="premium_check", value="disabled")
                session.add(setting)
            else:
                setting.value = "disabled"
            session.commit()

        await update.message.reply_text("✅ Controllo premium disattivato con successo.")

    except BadRequest as e:
        logger.error(f"Errore API: {str(e)}")
    except Exception as e:
        logger.error(f"Errore generale: {str(e)}", exc_info=True)
