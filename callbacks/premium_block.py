import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, ChatMember
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from database.db_manager import get_db_session, PremiumUser, is_premium_check_enabled
from datetime import datetime, timedelta, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

Link = config.BOOST_LINK

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MESSAGE = (
    "🔎 Ho rilevato <u>Telegram Premium</u> 🌟 per poter continuare serve <b>almeno un boost</b> ➕ al gruppo.\n\n"
    "⚠️ Successivamente, <b>premi il secondo pulsante</b> dopo aver boostato per essere smutato!\n\n"
    "<b>• Sei stato mutato per 5 minuti!</b>"
)

KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🚀 Potenzia il gruppo", url=Link)],
    [InlineKeyboardButton("✅ L'ho già fatto", callback_data="unmute_me_v2:{user_id}")],
])

MUTE_DURATION = timedelta(minutes=5)

async def check_premium_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    chat = update.effective_chat

    if not user or not user.is_premium:
        return

    with get_db_session() as session:
        # Verifica se il controllo premium è attivo
        if not is_premium_check_enabled(session):
            logger.info("Controllo premium disattivato, salto il mute.")
            return

        try:
            # Controlla se l'utente è admin/owner
            try:
                chat_member = await context.bot.get_chat_member(chat.id, user.id)
                if chat_member.status in ['creator', 'administrator']:
                    logger.info(f"Salto mute per admin/owner: {user.id}")
                    return
            except BadRequest as e:
                logger.error(f"Errore controllo stato utente: {str(e)}")
                return

            db_user = session.query(PremiumUser).filter(PremiumUser.user_id == user.id).first()

            # Registra nuovo utente se necessario
            if not db_user:
                db_user = PremiumUser(user_id=user.id, has_boosted=False)
                session.add(db_user)
                session.commit()
                logger.info(f"Nuovo utente premium registrato: {user.id}")

            if db_user.has_boosted:
                return

            # Calcola la data di scadenza del mute
            until_date = int((datetime.now(timezone.utc) + MUTE_DURATION).timestamp())

            # Applica restrizioni complete
            try:
                await context.bot.restrict_chat_member(
                    chat_id=chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_send_audios=False,
                        can_send_documents=False,
                        can_send_photos=False,
                        can_send_videos=False,
                        can_send_video_notes=False,
                        can_send_voice_notes=False,
                        can_send_polls=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                        can_change_info=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_manage_topics=False
                    ),
                    until_date=until_date
                )
                
                # Aggiorna il pulsante con il user_id
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Potenzia il gruppo", url=Link)],
                    [InlineKeyboardButton("✅ L'ho già fatto", callback_data=f"unmute_me_v2:{user.id}")]
                ])
                
                await update.message.reply_text(MESSAGE, reply_markup=keyboard, parse_mode="HTML")
                logger.info(f"Utente {user.id} mutato correttamente fino a {until_date}")

            except BadRequest as e:
                if "Can't remove chat owner" in str(e):
                    logger.warning(f"Tentativo di mutare il proprietario: {user.id}")
                else:
                    logger.error(f"Errore API durante il mute: {str(e)}")
                    raise

        except Exception as e:
            logger.error(f"Errore generale durante il mute: {str(e)}", exc_info=True)
            session.rollback()
            try:
                await update.message.reply_text("❌ Si è verificato un errore durante l'operazione")
            except Exception as e:
                logger.error(f"Errore invio messaggio: {str(e)}")
