import asyncio
import re
import logging
import signal
import sys
from telegram import Update, MessageEntity
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from telegram.error import Forbidden, RetryAfter, BadRequest
import config
import database as db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flags
shutdown_flag = False
application = None

# Telegram message link pattern
TELEGRAM_LINK_PATTERN = re.compile(
    r'(?:https?://)?(?:t\.me|telegram\.me)/(?:c/)?(\d+|[a-zA-Z][a-zA-Z0-9_]*)/(\d+)'
)


def utf16_len(text: str) -> int:
    """UTF-16 code unit uzunluğunu hesapla."""
    if not text:
        return 0
    return len(text.encode('utf-16-le')) // 2


# Link entity tipleri (silinecek)
LINK_ENTITY_TYPES = (
    MessageEntity.TEXT_LINK,
    MessageEntity.URL,
    MessageEntity.MENTION
)

# Formatting entity tipleri (korunacak)
FORMATTING_ENTITY_TYPES = (
    MessageEntity.BOLD,
    MessageEntity.ITALIC,
    MessageEntity.CODE,
    MessageEntity.PRE,
    MessageEntity.UNDERLINE,
    MessageEntity.STRIKETHROUGH,
    MessageEntity.SPOILER,
    MessageEntity.CUSTOM_EMOJI,
    MessageEntity.BLOCKQUOTE
)


async def parse_telegram_link(link: str) -> tuple:
    """Telegram mesaj linkini parse et ve (chat_id, message_id) döndür"""
    match = TELEGRAM_LINK_PATTERN.search(link)
    if not match:
        return None, None

    chat_identifier = match.group(1)
    message_id = int(match.group(2))

    if chat_identifier.isdigit():
        chat_id = int(f"-100{chat_identifier}")
    else:
        chat_id = f"@{chat_identifier}"

    return chat_id, message_id


def check_trigger_keywords(text: str, keywords_str: str) -> bool:
    """Mesajda trigger keyword var mı kontrol et"""
    if not keywords_str or not keywords_str.strip():
        return True

    if not text:
        return False

    text_lower = text.lower()
    keywords = [kw.strip().lower() for kw in keywords_str.split(',') if kw.strip()]

    if not keywords:
        return True

    for keyword in keywords:
        if keyword in text_lower:
            return True

    return False


def remove_links_from_text(text: str, entities: list) -> tuple:
    """
    Mesajdan link içeren SATIRLARI kaldır.
    Formatting entity'lerini koru.
    """
    if not text:
        return "", []

    if not entities:
        return text, []

    # Entity'leri kategorize et
    link_entities = []
    formatting_entities = []

    for entity in entities:
        if entity.type in LINK_ENTITY_TYPES:
            link_entities.append(entity)
        elif entity.type in FORMATTING_ENTITY_TYPES:
            formatting_entities.append(entity)

    # Link yoksa orijinali döndür
    if not link_entities:
        return text, list(formatting_entities)

    # Satırları bul
    lines = text.split('\n')

    # Her satırın UTF-16 başlangıç ve bitiş pozisyonlarını hesapla
    line_positions_utf16 = []
    current_pos_utf16 = 0
    for line in lines:
        line_len_utf16 = utf16_len(line)
        line_end_utf16 = current_pos_utf16 + line_len_utf16
        line_positions_utf16.append((current_pos_utf16, line_end_utf16))
        current_pos_utf16 = line_end_utf16 + 1  # +1 for \n

    # Link içeren satırları bul
    lines_to_remove = set()

    for entity in link_entities:
        link_start = entity.offset
        link_end = entity.offset + entity.length

        for line_idx, (start, end) in enumerate(line_positions_utf16):
            if link_start <= end and link_end >= start:
                lines_to_remove.add(line_idx)

    # Link içermeyen satırları birleştir
    cleaned_lines = []
    for idx, line in enumerate(lines):
        if idx not in lines_to_remove:
            cleaned_lines.append(line)

    cleaned_text = '\n'.join(cleaned_lines)

    # Boş satırları temizle
    while '\n\n\n' in cleaned_text:
        cleaned_text = cleaned_text.replace('\n\n\n', '\n\n')

    # Formatting entity'lerini filtrele ve güncelle
    updated_formatting = []
    for entity in formatting_entities:
        entity_start = entity.offset
        entity_end = entity.offset + entity.length

        entity_in_removed_line = False
        for line_idx in lines_to_remove:
            start, end = line_positions_utf16[line_idx]
            if entity_start <= end and entity_end >= start:
                entity_in_removed_line = True
                break

        if not entity_in_removed_line:
            adjustment = 0
            for line_idx in sorted(lines_to_remove):
                start, end = line_positions_utf16[line_idx]
                line_utf16_len = (end - start) + 1
                if start < entity_start:
                    adjustment += line_utf16_len

            new_offset = entity_start - adjustment
            cleaned_text_utf16_len = utf16_len(cleaned_text)

            if new_offset >= 0 and new_offset < cleaned_text_utf16_len:
                updated_formatting.append(MessageEntity(
                    type=entity.type,
                    offset=new_offset,
                    length=entity.length,
                    url=entity.url if hasattr(entity, 'url') else None,
                    user=entity.user if hasattr(entity, 'user') else None,
                    language=entity.language if hasattr(entity, 'language') else None,
                    custom_emoji_id=entity.custom_emoji_id if hasattr(entity, 'custom_emoji_id') else None
                ))

    return cleaned_text.strip(), updated_formatting


async def forward_message_via_bot(context: ContextTypes.DEFAULT_TYPE, source_channel_config: dict,
                                   from_chat_id: int, message_id: int,
                                   source_event_chat_id=None, source_event_message_id=None):
    """
    Bot API ile mesajı kopyala.
    copy_message kullanarak premium emojiler korunur!
    """
    try:
        target_chat_id_raw = source_channel_config['target_chat_id']
        try:
            target_chat_id = int(target_chat_id_raw)
        except (ValueError, TypeError):
            target_chat_id = target_chat_id_raw

        append_link = source_channel_config.get('append_link')
        append_link_text = source_channel_config.get('append_link_text', '')
        remove_links = source_channel_config.get('remove_links', False)
        trigger_keywords = source_channel_config.get('trigger_keywords', '')
        send_link_back = source_channel_config.get('send_link_back', False)

        # Önce mesajı al (caption/text kontrolü için)
        try:
            # Bot'un mesajı görebilmesi için kanalda olması gerekir
            # Eğer göremiyorsa direkt copy dene
            pass
        except Exception:
            pass

        # copy_message kullan - premium emojiler korunur!
        # NOT: copy_message ile caption değiştiremezsin, ama emojiler korunur

        if not remove_links and not append_link:
            # Direkt kopyala - en temiz yöntem
            sent_message = await context.bot.copy_message(
                chat_id=target_chat_id,
                from_chat_id=from_chat_id,
                message_id=message_id
            )
        else:
            # Link kaldırma veya ekleme gerekiyorsa, önce mesajı forward et
            # sonra düzenle - VEYA send_message ile yeniden gönder
            # Ama bu durumda premium emojiler kaybolabilir

            # En iyi çözüm: copy_message + ayrı mesaj olarak link
            sent_message = await context.bot.copy_message(
                chat_id=target_chat_id,
                from_chat_id=from_chat_id,
                message_id=message_id
            )

            # Append link varsa ayrı mesaj olarak gönder
            if append_link:
                link_text = append_link_text if append_link_text else append_link
                try:
                    await context.bot.send_message(
                        chat_id=target_chat_id,
                        text=f"🔗 {link_text}",
                        disable_web_page_preview=True,
                        reply_to_message_id=sent_message.message_id
                    )
                except Exception:
                    pass

        # Source link oluştur
        if str(from_chat_id).startswith('-100'):
            source_link = f"t.me/c/{str(from_chat_id)[4:]}/{message_id}"
        else:
            source_link = f"t.me/{from_chat_id}/{message_id}"

        # Target link oluştur
        if str(target_chat_id).startswith('-100'):
            target_link = f"https://t.me/c/{str(target_chat_id)[4:]}/{sent_message.message_id}"
        else:
            target_link = f"https://t.me/{target_chat_id}/{sent_message.message_id}"

        # Database'e kaydet
        await db.add_post(
            source_channel_id=source_channel_config['id'],
            source_link=source_link,
            source_chat_id=from_chat_id,
            source_message_id=message_id,
            target_chat_id=target_chat_id,
            target_message_id=sent_message.message_id,
            message_text=None,
            has_media=False,
            media_type=None,
            status='success'
        )

        # Send link back
        if send_link_back and source_event_chat_id and target_link:
            try:
                remaining_posts = await db.get_remaining_posts_today(source_channel_config['id'])
                feedback_message = f"✅ Post gönderildi!\n{target_link}\n📊 Kalan Post Hakkınız: {remaining_posts}"

                await context.bot.send_message(
                    chat_id=source_event_chat_id,
                    text=feedback_message,
                    reply_to_message_id=source_event_message_id,
                    disable_web_page_preview=True
                )
            except Exception:
                pass

        logger.info(f"✅ {message_id} -> {target_link}")
        return True

    except RetryAfter as e:
        logger.warning(f"Flood wait: {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
        return False

    except Forbidden:
        logger.error(f"Cannot write to {target_chat_id} - Bot not admin or blocked")
        await db.add_post(
            source_channel_id=source_channel_config['id'],
            source_link=f"t.me/{from_chat_id}/{message_id}",
            source_chat_id=from_chat_id,
            source_message_id=message_id,
            target_chat_id=target_chat_id,
            target_message_id=0,
            status='failed',
            has_media=False
        )
        return False

    except BadRequest as e:
        logger.error(f"Bad request: {e}")
        return False

    except Exception as e:
        logger.error(f"Forward error: {e}")
        return False


async def handle_telegram_link(update: Update, context: ContextTypes.DEFAULT_TYPE, link: str):
    """Telegram mesaj linkini işle"""
    try:
        chat_id, message_id = await parse_telegram_link(link)

        if not chat_id or not message_id:
            return

        source_channel = await db.get_source_channel(update.effective_chat.id)

        if not source_channel:
            return

        can_post = await db.can_post_today(source_channel['id'])
        if not can_post:
            if source_channel.get('send_link_back', False):
                try:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="⚠️ Günlük post limitiniz doldu. Yarın tekrar deneyin.",
                        reply_to_message_id=update.message.message_id,
                        disable_web_page_preview=True
                    )
                except Exception:
                    pass
            return

        # Trigger keywords kontrolü
        message_text = update.message.text or update.message.caption or ''
        trigger_keywords = source_channel.get('trigger_keywords', '')
        if not check_trigger_keywords(message_text, trigger_keywords):
            return

        await forward_message_via_bot(
            context,
            source_channel,
            chat_id if isinstance(chat_id, int) else chat_id,
            message_id,
            source_event_chat_id=update.effective_chat.id,
            source_event_message_id=update.message.message_id
        )

    except Exception as e:
        logger.error(f"Link error: {e}")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm mesajları işle"""
    try:
        if not update.message:
            return

        if not await db.is_bot_enabled():
            return

        source_channel = await db.get_source_channel(update.effective_chat.id)

        if not source_channel:
            return

        message_text = update.message.text or update.message.caption or ''
        listen_type = source_channel.get('listen_type', 'direct')

        if listen_type == 'link':
            # Link dinleme modu - mesajdaki linkleri işle
            links = TELEGRAM_LINK_PATTERN.findall(message_text)

            if links:
                for match in TELEGRAM_LINK_PATTERN.finditer(message_text):
                    full_link = match.group(0)
                    await handle_telegram_link(update, context, full_link)

        else:  # listen_type == 'direct'
            # Direkt mesaj modu - mesajı olduğu gibi kopyala
            if message_text or update.message.photo or update.message.video or update.message.document:
                can_post = await db.can_post_today(source_channel['id'])
                if not can_post:
                    if source_channel.get('send_link_back', False):
                        try:
                            await context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text="⚠️ Günlük post limitiniz doldu. Yarın tekrar deneyin.",
                                reply_to_message_id=update.message.message_id,
                                disable_web_page_preview=True
                            )
                        except Exception:
                            pass
                    return

                # Trigger keywords kontrolü
                trigger_keywords = source_channel.get('trigger_keywords', '')
                if not check_trigger_keywords(message_text, trigger_keywords):
                    return

                await forward_message_via_bot(
                    context,
                    source_channel,
                    update.effective_chat.id,
                    update.message.message_id,
                    source_event_chat_id=update.effective_chat.id,
                    source_event_message_id=update.message.message_id
                )

    except Exception as e:
        import traceback
        logger.error(f"Handler error: {e}\n{traceback.format_exc()}")


async def update_bot_status(status: str):
    """Bot durumunu database'de güncelle"""
    try:
        await db.set_setting('bot_status', status)
    except Exception:
        pass


async def heartbeat():
    """Periyodik heartbeat"""
    global shutdown_flag

    while not shutdown_flag:
        try:
            await update_bot_status('online')
        except Exception:
            pass

        await asyncio.sleep(config.HEARTBEAT_INTERVAL)


async def post_init(app: Application):
    """Bot başlatıldıktan sonra çalışır"""
    await db.init_db()
    await update_bot_status('online')

    # Heartbeat task başlat
    asyncio.create_task(heartbeat())

    me = await app.bot.get_me()
    logger.info(f"✅ Bot @{me.username} başlatıldı!")


async def post_shutdown(app: Application):
    """Bot kapanırken çalışır"""
    global shutdown_flag
    shutdown_flag = True

    await update_bot_status('offline')
    await db.close_db()
    logger.info("Bot kapatıldı.")


def main():
    """Ana fonksiyon"""
    global application

    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN required!")
        sys.exit(1)

    if not config.DATABASE_URL:
        logger.error("DATABASE_URL required!")
        sys.exit(1)

    # Application oluştur
    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Handler ekle - tüm mesajları dinle
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        message_handler
    ))

    logger.info("🚀 Bot başlatılıyor...")

    # Polling ile çalıştır
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == '__main__':
    main()
