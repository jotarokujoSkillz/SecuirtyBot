from datetime import datetime, timedelta, timezone
import re
import asyncio
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from utils import resolve_target, verified_boosters, recently_muted, send_private_or_group_message

DEFAULT_MUTE_DURATION = timedelta(minutes=5)  # Tempo di mute predefinito
MAX_MUTE_DURATION = timedelta(hours=24)       # Limite massimo di mute (24 ore)

async def send_temp_message(chat_id, bot, text, delay=10):
    """Invia un messaggio temporaneo che viene cancellato automaticamente dopo `delay` secondi."""
    message = await bot.send_message(chat_id=chat_id, text=text)
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

def parse_duration(time_str: str) -> timedelta:
    time_str = time_str.strip()
    # Modifica il pattern per supportare durate concatenate (es. 1h10m)
    pattern = re.compile(r'(\d+)([hms])')
    parts = pattern.findall(time_str)

    if not parts:
        raise ValueError("Formato tempo non valido. Usa ad esempio: 5m, 1h30m, 30s o 1h 30m 20s.")

    hours = 0
    minutes = 0
    seconds = 0

    for amount, unit in parts:
        amount = int(amount)
        if amount <= 0:
            raise ValueError("Il tempo deve essere positivo.")

        if unit == 'h':
            if amount > 24:
                raise ValueError("Le ore non possono superare 24.")
            hours += amount
        elif unit == 'm':
            if amount > 60:
                raise ValueError("I minuti non possono superare 60.")
            minutes += amount
        elif unit == 's':
            if amount > 60:
                raise ValueError("I secondi non possono superare 60.")
            seconds += amount

    total_seconds = hours * 3600 + minutes * 60 + seconds

    if total_seconds <= 0:
        raise ValueError("Il tempo deve essere positivo.")

    if total_seconds > MAX_MUTE_DURATION.total_seconds():
        raise ValueError(f"Il tempo massimo consentito è {format_duration(MAX_MUTE_DURATION)}.")

    return timedelta(seconds=total_seconds)


def format_duration(duration: timedelta) -> str:
    seconds = duration.total_seconds()
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{int(hours)} ora" if hours == 1 else f"{int(hours)} ore")
    if minutes > 0:
        parts.append(f"{int(minutes)} minuto" if minutes == 1 else f"{int(minutes)} minuti")
    if seconds > 0:
        parts.append(f"{int(seconds)} secondo" if seconds == 1 else f"{int(seconds)} secondi")
    
    if not parts:
        return "0 secondi"
    return " e ".join(parts)

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = msg.chat
    issuer = msg.from_user

    # Verifica permessi admin
    try:
        member = await context.bot.get_chat_member(chat.id, issuer.id)
        if member.status not in ("administrator", "creator"):
            result = await send_private_or_group_message(
                issuer_id=issuer.id,
                chat_id=chat.id,
                bot=context.bot,
                text="❌ Solo gli admin possono usare /blocca."
            )
            if result == "group":
                try:
                    await msg.delete()
                except:
                    pass
            return
    except Exception:
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Errore di verifica permessi."
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
        return

    # Determina il tempo di mute
    # Estrai e valida la durata se presente
    # Cerca tutte le durate (sia attaccate che separate)
    duration = None
    joined_args = " ".join(context.args)
    matches = re.findall(r'\d+[hms]', joined_args)
    if matches:
        try:
            duration = parse_duration(' '.join(matches))
            for part in matches:
                joined_args = joined_args.replace(part, '', 1)
            context.args = joined_args.strip().split()
        except ValueError as e:
            sent_in_private = await send_private_or_group_message(
                issuer_id=issuer.id,
                chat_id=chat.id,
                bot=context.bot,
                text=f"❌ {e}\nEsempi validi: 5m, 1h30m, 30s, 1h 10m 20s."
            )
            if sent_in_private:
                try:
                    await msg.delete()
                except:
                    pass
            return
    else:
        duration = DEFAULT_MUTE_DURATION




    # Risoluzione target
    try:
        target = await resolve_target(update, context)
    except Exception:
        target = None

    if not target:
        sent_in_private = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="🔍 Specificare un utente valido (risposta, @username o ID).\n"
                 "Esempi:\n"
                 "/blocca 5m (risposta)\n"
                 "/blocca @username 10m\n"
                 "/blocca 123456789 1h"
        )
        if sent_in_private:
            try:
                await msg.delete()
            except:
                pass
        return

    # Controllo admin target
    try:
        target_member = await context.bot.get_chat_member(chat.id, target.id)
        if target_member.status in ("administrator", "creator"):
            return await send_private_or_group_message(
                issuer_id=issuer.id,
                chat_id=chat.id,
                bot=context.bot,
                text="❌ Non posso mutare un admin!"
            )
    except:
        return await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Utente non trovato."
        )

    # Applica mute
    try:
        until = datetime.now(timezone.utc) + duration
        await context.bot.restrict_chat_member(
            chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
        recently_muted[target.id] = datetime.now(timezone.utc)
        await msg.reply_text(f"🔇 {target.full_name} mutato per {format_duration(duration)}.")
    except Exception as e:
        await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Errore durante il mute."
        )
        raise e


async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat = msg.chat
    issuer = msg.from_user

    # Verifica permessi admin
    try:
        member = await context.bot.get_chat_member(chat.id, issuer.id)
        if member.status not in ("administrator", "creator"):
            result = await send_private_or_group_message(
                issuer_id=issuer.id,
                chat_id=chat.id,
                bot=context.bot,
                text="❌ Solo gli admin possono usare /libera."
            )
            if result == "group":
                try:
                    await msg.delete()
                except:
                    pass
            return
    except:
        result = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Errore di verifica permessi."
        )
        if result == "group":
            try:
                await msg.delete()
            except:
                pass
        return

    # Risoluzione target
    try:
        target = await resolve_target(update, context)
    except:
        target = None

    if not target:
        sent_in_private = await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="🔍 Specificare un utente valido (risposta, @username o ID).\n"
                 "Esempi:\n"
                 "/libera (risposta)\n"
                 "/libera @username\n"
                 "/libera 123456789"
        )
        if sent_in_private:
            try:
                await msg.delete()
            except:
                pass
        return

    # Controllo admin target
    try:
        target_member = await context.bot.get_chat_member(chat.id, target.id)
        if target_member.status in ("administrator", "creator"):
            return await send_private_or_group_message(
                issuer_id=issuer.id,
                chat_id=chat.id,
                bot=context.bot,
                text="❌ Non posso smutare un admin!"
            )
    except:
        return await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Utente non trovato."
        )

    # Rimuovi mute
    try:
        await context.bot.restrict_chat_member(
            chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        verified_boosters.add(target.id)
        await msg.reply_text(f"✅ {target.full_name} smutato con successo!")
    except Exception as e:
        await send_private_or_group_message(
            issuer_id=issuer.id,
            chat_id=chat.id,
            bot=context.bot,
            text="❌ Errore durante lo smute."
        )
        raise e
