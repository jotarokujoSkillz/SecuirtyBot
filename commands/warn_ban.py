# /commands/warn_ban.py

import logging
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ContextTypes
from utils import resolve_target, send_private_or_group_message

logger = logging.getLogger(__name__)

# Stato temporaneo in RAM
user_warns = {}  # user_id -> [datetime1, datetime2, ...]

MAX_WARNS = 3

# ——— /warn ——————————————————————————————
async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = msg.chat
    issuer = msg.from_user

    member = await context.bot.get_chat_member(chat.id, issuer.id)
    if member.status not in ("administrator", "creator"):
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Solo admin possono usare /rwarn."
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
        return

    target = await resolve_target(update, context)
    if not target:
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="Uso: /rwarn [rispondi a un messaggio / user_id / @username]"
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
        return

    if (await context.bot.get_chat_member(chat.id, target.id)).status in ("administrator", "creator"):
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Non posso avvisare un admin."
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
        return

    now = datetime.now(timezone.utc)
    warns = user_warns.setdefault(target.id, [])
    warns.append(now)

    if len(warns) >= MAX_WARNS:
        try:
            await context.bot.ban_chat_member(chat.id, target.id)
            user_warns.pop(target.id, None)
            await msg.reply_text(f"🚫 {target.full_name} è stato bannato (3/3 avvisi).")
            logger.info("User %s bannato per 3 warn", target.id)
        except Exception as e:
            logger.error("Errore nel bannare %s: %s", target.id, e)
            await send_private_or_group_message(
                issuer_id=issuer.id,
                chat_id=chat.id,
                bot=context.bot,
                text="❌ Errore nel bannare."
            )
    else:
        await msg.reply_text(f"⚠️ {target.full_name} ha ricevuto un avviso ({len(warns)}/{MAX_WARNS})")

# ——— /ban ——————————————————————————————
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = msg.chat
    issuer = msg.from_user

    member = await context.bot.get_chat_member(chat.id, issuer.id)
    if member.status not in ("administrator", "creator"):
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Solo admin possono usare /rban."
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
        return

    target = await resolve_target(update, context)
    if not target:
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="Uso: /rban [rispondi a un messaggio / user_id / @username]"
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
        return

    if (await context.bot.get_chat_member(chat.id, target.id)).status in ("administrator", "creator"):
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Non posso bannare un admin."
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
        return

    try:
        await context.bot.ban_chat_member(chat.id, target.id)
        user_warns.pop(target.id, None)
        await msg.reply_text(f"🚫 {target.full_name} è stato bannato.")
        logger.info("User %s bannato con /rban", target.id)
    except Exception as e:
        logger.error("Errore /rban %s: %s", target.id, e)
        await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Errore nel bannare."
        )

# ——— /unwarn ——————————————————————————————
async def unwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = msg.chat
    issuer = msg.from_user

    member = await context.bot.get_chat_member(chat.id, issuer.id)
    if member.status not in ("administrator", "creator"):
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Solo admin possono usare /unwarn."
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
        return

    target = await resolve_target(update, context)
    if not target:
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="Uso: /runwarn [rispondi a un messaggio / user_id / @username] [numero di avvisi da rimuovere]"
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
        return

    try:
        num_warns_to_remove = int(context.args[1]) if len(context.args) > 1 else 1
        warns = user_warns.get(target.id, [])
        if not warns:
            await msg.reply_text(f"ℹ️ {target.full_name} non ha avvisi.")
            return

        removed_warns = min(num_warns_to_remove, len(warns))
        user_warns[target.id] = warns[removed_warns:]
        await msg.reply_text(f"✅ Rimossi {removed_warns} avvisi per {target.full_name}.")
    except ValueError:
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Numero di avvisi da rimuovere non valido. Usa un numero intero."
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
    except Exception as e:
        logger.error("Errore /runwarn %s: %s", target.id, e)
        await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Errore durante la rimozione degli avvisi."
        )
