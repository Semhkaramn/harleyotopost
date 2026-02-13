import asyncio
import re
import logging
import signal
import sys
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageEntityTextUrl,
    MessageEntityUrl,
    MessageEntityMention,
    MessageEntityCustomEmoji,
    MessageEntityBold,
    MessageEntityItalic,
    MessageEntityCode,
    MessageEntityPre,
    MessageEntityUnderline,
    MessageEntityStrike,
    MessageEntitySpoiler,
    MessageEntityBlockquote,
)
from telethon.errors import (
    FloodWaitError,
    ChatWriteForbiddenError,
    AuthKeyUnregisteredError,
    UserDeactivatedBanError
)
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
client = None

# Telegram message link pattern
TELEGRAM_LINK_PATTERN = re.compile(
    r'(?:https?://)?(?:t\.me|telegram\.me)/(?:c/)?(\d+|[a-zA-Z][a-zA-Z0-9_]*)/(\d+)'
)

# Link entity tipleri (silinecek)
LINK_ENTITY_TYPES = (MessageEntityTextUrl, MessageEntityUrl, MessageEntityMention)

# Formatting entity tipleri (korunacak)
FORMATTING_ENTITY_TYPES = (
    MessageEntityBold, MessageEntityItalic, MessageEntityCode,
    MessageEntityPre, MessageEntityUnderline, MessageEntityStrike,
    MessageEntitySpoiler, MessageEntityCustomEmoji, MessageEntityBlockquote
)


def create_client():
    """Create Telegram client with StringSession"""
    if not config.SESSION_STRING:
        logger.error("SESSION_STRING is required!")
        sys.exit(1)

    session = StringSession(config.SESSION_STRING)

    return TelegramClient(
        session,
        config.API_ID,
        config.API_HASH,
        connection_retries=5,
        retry_delay=1,
        auto_reconnect=True
    )


def remove_links_from_message(raw_text: str, entities: list) -> tuple:
    """
    Mesajdan link entity'lerini içeren SATIRLARI tamamen kaldır.
    Formatting entity'lerini (bold, italic, custom emoji vb.) koru.

    Args:
        raw_text: Mesajın düz metni (message.raw_text)
        entities: Mesajın entity listesi

    Returns:
        (temizlenmiş_metin, güncellenmiş_entity_listesi)
    """
    if not raw_text:
        return "", []

    if not entities:
        return raw_text, []

    # Entity'leri kategorize et
    link_entities = []
    formatting_entities = []

    for entity in entities:
        if isinstance(entity, LINK_ENTITY_TYPES):
            link_entities.append(entity)
        elif isinstance(entity, FORMATTING_ENTITY_TYPES):
            formatting_entities.append(entity)
        else:
            # Bilinmeyen ama link olmayan entity'leri de koru
            formatting_entities.append(entity)

    # Link yoksa orijinali döndür
    if not link_entities:
        return raw_text, formatting_entities

    # Satırları bul
    lines = raw_text.split('\n')

    # Her link entity'sinin hangi satırda olduğunu bul
    lines_to_remove = set()

    for entity in link_entities:
        # UTF-16 offset'i karakter pozisyonuna çevir
        link_start = entity.offset

        # Link'in hangi satırda olduğunu bul
        current_pos = 0
        for line_idx, line in enumerate(lines):
            line_end = current_pos + len(line)
            if current_pos <= link_start < line_end + 1:  # +1 for \n
                lines_to_remove.add(line_idx)
                break
            current_pos = line_end + 1  # +1 for \n

    # Link içermeyen satırları birleştir
    cleaned_lines = []
    for idx, line in enumerate(lines):
        if idx not in lines_to_remove:
            cleaned_lines.append(line)

    cleaned_text = '\n'.join(cleaned_lines)

    # Boş satırları temizle (ardışık boş satırları tek satıra indir)
    while '\n\n\n' in cleaned_text:
        cleaned_text = cleaned_text.replace('\n\n\n', '\n\n')

    # Formatting entity'lerini güncelle - link satırları silindikten sonra offset'leri ayarla
    # Not: Bu basit bir yaklaşım - karmaşık formatlama için daha detaylı işlem gerekebilir
    updated_formatting = []
    removed_chars = 0
    current_pos = 0

    for line_idx, line in enumerate(lines):
        line_len = len(line) + 1  # +1 for \n
        if line_idx in lines_to_remove:
            # Bu satır silindi, offset'leri güncelle
            for entity in formatting_entities:
                if entity.offset >= current_pos + line_len:
                    entity.offset -= line_len
            removed_chars += line_len
        current_pos += line_len

    # Sadece geçerli entity'leri tut
    for entity in formatting_entities:
        if entity.offset >= 0 and entity.length > 0:
            # Entity'nin pozisyonunun temizlenmiş metinde geçerli olup olmadığını kontrol et
            if entity.offset < len(cleaned_text):
                updated_formatting.append(entity)

    return cleaned_text.strip(), updated_formatting


def append_link_to_text(text: str, link: str, link_text: str = None) -> tuple:
    """
    Metnin sonuna link ekle.
    Eğer link_text verilmişse, Telegram'daki gibi metin üzerine link oluşturur.

    Args:
        text: Orijinal metin
        link: Eklenecek URL
        link_text: Link'in görünür metni (opsiyonel)

    Returns:
        (güncellenmiş_metin, ek_entity_listesi)
    """
    if not link:
        return text, []

    # Link metni varsa, metin olarak göster ve entity ekle
    if link_text and link_text.strip():
        display_text = link_text.strip()
    else:
        # Link metni yoksa, URL'yi doğrudan göster
        display_text = link

    if text:
        new_text = f"{text}\n\n{display_text}"
        # Link entity'si için offset hesapla (UTF-16)
        link_offset = len(text) + 2  # +2 for \n\n
    else:
        new_text = display_text
        link_offset = 0

    # Eğer link metni varsa, MessageEntityTextUrl oluştur
    entities = []
    if link_text and link_text.strip():
        # MessageEntityTextUrl entity'si oluştur
        entity = MessageEntityTextUrl(
            offset=link_offset,
            length=len(display_text),
            url=link
        )
        entities.append(entity)

    return new_text, entities


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
        chat_id = chat_identifier

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


async def forward_message(source_channel_config: dict, message, source_event_chat_id=None):
    """Mesajı hedef kanala işleyerek gönder"""
    global client

    try:
        target_chat_id = source_channel_config['target_chat_id']
        append_link = source_channel_config['append_link']
        append_link_text = source_channel_config.get('append_link_text', '')
        remove_links = source_channel_config['remove_links']
        trigger_keywords = source_channel_config.get('trigger_keywords', '')
        send_link_back = source_channel_config.get('send_link_back', False)

        # Orijinal metin ve entity'leri al
        # ÖNEMLİ: raw_text kullan, text değil!
        original_text = message.raw_text or ''
        original_entities = list(message.entities) if message.entities else []

        # Media için caption
        if not original_text and message.media:
            original_text = message.caption or ''
            original_entities = list(message.caption_entities) if message.caption_entities else []

        # Trigger keywords kontrolü
        if not check_trigger_keywords(original_text, trigger_keywords):
            return False

        # Link kaldırma işlemi
        if remove_links:
            final_text, final_entities = remove_links_from_message(original_text, original_entities)
        else:
            # Link kaldırma kapalı - orijinali kullan
            final_text = original_text
            final_entities = original_entities

        # Append link (link metni desteği ile)
        if append_link:
            final_text, link_entities = append_link_to_text(final_text, append_link, append_link_text)
            # Link entity'lerini mevcut entity'lere ekle
            if link_entities:
                final_entities = final_entities + link_entities

        # Media kontrolü
        has_media = message.media is not None
        media_type = None

        if has_media:
            if isinstance(message.media, MessageMediaPhoto):
                media_type = 'photo'
            elif isinstance(message.media, MessageMediaDocument):
                media_type = 'document'
            else:
                media_type = 'other'

        # Mesajı gönder
        # ÖNEMLİ: parse_mode=None ve formatting_entities kullan
        # Bu sayede metin olduğu gibi gönderilir, markdown parse edilmez

        if has_media:
            sent_message = await client.send_file(
                entity=target_chat_id,
                file=message.media,
                caption=final_text if final_text else None,
                formatting_entities=final_entities if final_entities else None,
                parse_mode=None  # Markdown/HTML parse YAPMA
            )
        else:
            sent_message = await client.send_message(
                entity=target_chat_id,
                message=final_text,
                formatting_entities=final_entities if final_entities else None,
                parse_mode=None,  # Markdown/HTML parse YAPMA
                link_preview=False
            )

        # Source link oluştur
        source_chat_id = message.chat_id
        try:
            source_entity = await client.get_entity(source_chat_id)
            source_username = getattr(source_entity, 'username', None)
            if source_username:
                source_link = f"t.me/{source_username}/{message.id}"
            elif str(source_chat_id).startswith('-100'):
                source_link = f"t.me/c/{str(source_chat_id)[4:]}/{message.id}"
            else:
                source_link = f"t.me/{source_chat_id}/{message.id}"
        except Exception:
            if str(source_chat_id).startswith('-100'):
                source_link = f"t.me/c/{str(source_chat_id)[4:]}/{message.id}"
            else:
                source_link = f"t.me/{source_chat_id}/{message.id}"

        # Target link oluştur
        target_link = None
        try:
            target_entity = await client.get_entity(target_chat_id)
            target_username = getattr(target_entity, 'username', None)
            if target_username:
                target_link = f"https://t.me/{target_username}/{sent_message.id}"
            elif str(target_chat_id).startswith('-100'):
                target_link = f"https://t.me/c/{str(target_chat_id)[4:]}/{sent_message.id}"
            else:
                target_link = f"https://t.me/{target_chat_id}/{sent_message.id}"
        except Exception:
            if str(target_chat_id).startswith('-100'):
                target_link = f"https://t.me/c/{str(target_chat_id)[4:]}/{sent_message.id}"
            else:
                target_link = f"https://t.me/{target_chat_id}/{sent_message.id}"

        # Send link back
        if send_link_back and source_event_chat_id and target_link:
            try:
                await client.send_message(source_event_chat_id, target_link)
            except Exception:
                pass

        # Database'e kaydet
        await db.add_post(
            source_channel_id=source_channel_config['id'],
            source_link=source_link,
            source_chat_id=source_chat_id,
            source_message_id=message.id,
            target_chat_id=target_chat_id,
            target_message_id=sent_message.id,
            message_text=final_text[:500] if final_text else None,
            has_media=has_media,
            media_type=media_type,
            status='success'
        )

        logger.info(f"✅ {message.id} -> {target_link}")
        return True

    except FloodWaitError as e:
        logger.warning(f"Flood wait: {e.seconds}s")
        await asyncio.sleep(e.seconds)
        return False

    except ChatWriteForbiddenError:
        logger.error(f"Cannot write to {target_chat_id}")
        await db.add_post(
            source_channel_id=source_channel_config['id'],
            source_link=f"t.me/{message.chat_id}/{message.id}",
            source_chat_id=message.chat_id,
            source_message_id=message.id,
            target_chat_id=target_chat_id,
            target_message_id=0,
            status='failed',
            has_media=False
        )
        return False

    except Exception as e:
        logger.error(f"Forward error: {e}")
        return False


async def handle_telegram_link(event, link: str):
    """Telegram mesaj linkini işle - mesajı al ve forward et"""
    global client

    try:
        chat_id, message_id = await parse_telegram_link(link)

        if not chat_id or not message_id:
            return

        try:
            if isinstance(chat_id, str):
                entity = await client.get_entity(chat_id)
                message = await client.get_messages(entity, ids=message_id)
            else:
                message = await client.get_messages(chat_id, ids=message_id)
        except Exception:
            return

        if not message:
            return

        source_channel = await db.get_source_channel(event.chat_id)

        if not source_channel:
            return

        can_post = await db.can_post_today(source_channel['id'])
        if not can_post:
            return

        await forward_message(source_channel, message, source_event_chat_id=event.chat_id)

    except Exception as e:
        logger.error(f"Link error: {e}")


async def setup_message_handler():
    """Mesaj handler'ını kur"""
    global client

    @client.on(events.NewMessage)
    async def message_handler(event):
        """Monitör edilen kanallardaki yeni mesajları işle"""
        try:
            if not await db.is_bot_enabled():
                return

            source_channel = await db.get_source_channel(event.chat_id)

            if not source_channel:
                return

            message_text = event.message.raw_text or event.message.caption or ''
            listen_type = source_channel.get('listen_type', 'direct')

            if listen_type == 'link':
                links = TELEGRAM_LINK_PATTERN.findall(message_text)

                if links:
                    for match in TELEGRAM_LINK_PATTERN.finditer(message_text):
                        full_link = match.group(0)
                        await handle_telegram_link(event, full_link)

            else:  # listen_type == 'direct'
                if message_text or event.message.media:
                    can_post = await db.can_post_today(source_channel['id'])
                    if not can_post:
                        return

                    await forward_message(source_channel, event.message, source_event_chat_id=event.chat_id)

        except Exception as e:
            logger.error(f"Handler error: {e}")


async def update_bot_status(status: str):
    """Bot durumunu database'de güncelle"""
    try:
        await db.set_setting('bot_status', status)
    except Exception:
        pass


async def heartbeat():
    """Periyodik heartbeat - bot durumunu güncelle"""
    global shutdown_flag

    while not shutdown_flag:
        try:
            await update_bot_status('online')
        except Exception:
            pass

        await asyncio.sleep(config.HEARTBEAT_INTERVAL)


async def graceful_shutdown(sig=None):
    """Graceful shutdown işle"""
    global shutdown_flag, client

    shutdown_flag = True

    try:
        await update_bot_status('offline')
    except Exception:
        pass

    if client and client.is_connected():
        try:
            await client.disconnect()
        except Exception:
            pass

    try:
        await db.close_db()
    except Exception:
        pass


def setup_signal_handlers(loop):
    """Signal handler'ları kur"""
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(graceful_shutdown(s))
            )
        except NotImplementedError:
            signal.signal(sig, lambda s, f: asyncio.create_task(graceful_shutdown()))


async def start_client():
    """Telegram client'ı başlat"""
    global client

    await client.connect()

    if not await client.is_user_authorized():
        logger.error("Session expired! Run: python generate_session.py")
        raise AuthKeyUnregisteredError("Session expired or invalid")

    return client


async def main():
    """Ana fonksiyon"""
    global client, shutdown_flag

    if not config.API_ID or not config.API_HASH:
        logger.error("API_ID and API_HASH required!")
        sys.exit(1)

    if not config.DATABASE_URL:
        logger.error("DATABASE_URL required!")
        sys.exit(1)

    if not config.SESSION_STRING:
        logger.error("SESSION_STRING required!")
        sys.exit(1)

    try:
        await db.init_db()
    except Exception as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)

    client = create_client()

    try:
        await start_client()
    except (AuthKeyUnregisteredError, UserDeactivatedBanError) as e:
        logger.error(f"Auth failed: {e}")
        await db.close_db()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Client error: {e}")
        await db.close_db()
        sys.exit(1)

    try:
        me = await client.get_me()
        logger.info(f"✅ {me.first_name} (@{me.username or 'no username'}) - Bot running")
    except Exception:
        logger.info("✅ Bot running")

    await setup_message_handler()
    await update_bot_status('online')

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        await client.run_until_disconnected()
    except Exception as e:
        if not shutdown_flag:
            logger.error(f"Disconnected: {e}")

    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    setup_signal_handlers(loop)

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.run_until_complete(graceful_shutdown())
    except Exception as e:
        logger.error(f"Crashed: {e}")
        loop.run_until_complete(graceful_shutdown())
    finally:
        loop.close()
