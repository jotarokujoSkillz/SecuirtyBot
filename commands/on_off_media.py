from telegram import Update, ChatMemberOwner
from telegram.ext import ContextTypes
from antiflood.mediasystem import immune_users
from utils import resolve_target, send_private_or_group_message

async def immune_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = msg.chat
    user = msg.from_user

    if not user or not chat:
        return

    # Controlla se l'utente è un proprietario del gruppo
    chat_member = await context.bot.get_chat_member(chat.id, user.id)
    if not isinstance(chat_member, ChatMemberOwner):
        await send_private_or_group_message(
            issuer_id=user.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Solo il proprietario del gruppo può usare questo comando.",
            delay=None  # Evita la cancellazione automatica
        )
        return

    # Risolvi l'utente target
    target_user = await resolve_target(update, context)
    if not target_user:
        await send_private_or_group_message(
            issuer_id=user.id,
            chat_id=chat.id,
            bot=context.bot,
            text="⚠️ Impossibile trovare l'utente specificato.",
            delay=None  # Evita la cancellazione automatica
        )
        return

    target_user_id = target_user.id

    # Aggiungi o rimuovi l'utente dal set degli utenti immuni
    if target_user_id in immune_users:
        immune_users.remove(target_user_id)
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"❌ {target_user.first_name} non è più immune al sistema di cooldown."
        )
    else:
        immune_users.add(target_user_id)
        await context.bot.send_message(
            chat_id=chat.id,
            text=f"✅ {target_user.first_name} è ora immune al sistema di cooldown."
        )

async def immune_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # Controlla se l'utente è un proprietario del gruppo
    chat_member = await context.bot.get_chat_member(chat.id, user.id)
    if not isinstance(chat_member, ChatMemberOwner):
        await send_private_or_group_message(
            issuer_id=user.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Solo il proprietario del gruppo può usare questo comando.",
            delay=None  # Evita la cancellazione automatica
        )
        return

    if not immune_users:
        await context.bot.send_message(
            chat_id=chat.id,
            text="ℹ️ Nessun utente è attualmente immune al sistema di cooldown."
        )
        return

    immune_list = []
    for user_id in immune_users:
        try:
            chat_member = await context.bot.get_chat(user_id)
            if chat_member.username:
                display_name = f"@{chat_member.username}"  # Mostra l'username con "@"
            else:
                display_name = f"{chat_member.full_name} (ID: {user_id})"  # Nome utente e user_id
        except Exception:
            display_name = f"ID: {user_id}"  # Fallback in caso di errore
        immune_list.append(f"- {display_name}")

    immune_list_text = "\n".join(immune_list)
    await context.bot.send_message(
        chat_id=chat.id,
        text=f"🛡️ Utenti immuni al sistema di cooldown:\n{immune_list_text}"
    )
