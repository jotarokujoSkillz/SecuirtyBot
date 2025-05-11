# /callbacks/hasBoosted.py
from telegram import Update, ChatMemberOwner, ChatMemberAdministrator, ChatPermissions
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest, RetryAfter
from database.db_manager import get_db_session, PremiumUser
from datetime import datetime, timedelta, timezone
import logging
import asyncio

logger = logging.getLogger(__name__)

async def handle_unmute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        user = update.effective_user
        chat = update.effective_chat

        if not user or not chat:
            await query.answer("❌ Errore di sistema", show_alert=True)
            return

        # Estrai user_id dal callback data
        callback_data = query.data
        _, target_user_id = callback_data.split(":")
        target_user_id = int(target_user_id)

        if user.id != target_user_id:
            await query.answer("⚠️ Non sei autorizzato a sbloccare questo utente!", show_alert=True)
            return

        with get_db_session() as session:
            db_user = session.query(PremiumUser).filter(PremiumUser.user_id == target_user_id).first()

            if not db_user:
                await query.answer("⚠️ Utente non registrato", show_alert=True)
                return

            try:
                # 1. Controllo gerarchia
                chat_member = await context.bot.get_chat_member(chat.id, user.id)
                if isinstance(chat_member, (ChatMemberOwner, ChatMemberAdministrator)):
                    await query.answer("🔑 Sei admin/proprietario!", show_alert=True)
                    return

                # 2. Verifica boost utente nella chat specifica
                try:
                    boosts = await context.bot.get_user_chat_boosts(chat.id, user.id)
                    has_active_boost = any(
                        boost.source.source == "premium" and 
                        (datetime.now(timezone.utc) - boost.add_date).days < 365
                        for boost in boosts.boosts
                    )
                except RetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                    boosts = await context.bot.get_user_chat_boosts(chat.id, user.id)
                    has_active_boost = any(
                        boost.source.source == "premium" and 
                        (datetime.now(timezone.utc) - boost.add_date).days < 365
                        for boost in boosts.boosts
                    )

                if not has_active_boost:
                    await query.answer(
                        "🚫 Boost non attivo! Verifica di aver:"
                        "\n1. Boostato il gruppo corretto"
                        "\n2. Atteso 5 minuti",
                        show_alert=True
                    )
                    return

                # 3. Aggiornamento database e unmute
                db_user.has_boosted = True
                db_user.boost_verified_at = datetime.now(timezone.utc)
                session.commit()

                await context.bot.restrict_chat_member(
                    chat_id=chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions.all_permissions()
                )
                
                await query.answer("✅ Sbloccato con successo!", show_alert=True)
                await query.message.edit_reply_markup(reply_markup=None)

                # Messaggio di ringraziamento
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=f"🎉 Grazie {user.mention_html()} per aver potenziato il gruppo! 🚀",
                    parse_mode="HTML"
                )

            except BadRequest as e:
                logger.error(f"Errore API: {str(e)}")
                await query.answer("⚠️ Errore durante la verifica", show_alert=True)
                session.rollback()

    except Exception as e:
        logger.error(f"Errore generale: {str(e)}", exc_info=True)
        await query.answer("❌ Errore critico", show_alert=True)

def is_boost_active(add_date: datetime) -> bool:
    return (datetime.now(timezone.utc) - add_date).days < 365

unmute_callback_handler = CallbackQueryHandler(
    handle_unmute_callback, 
    pattern=r"^unmute_me_v2:\d+$",
    block=True  # Forza il blocco per testing
)
