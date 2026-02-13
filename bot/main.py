import asyncio
import re
import logging
import signal
import sys
import copy
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

# URL regex pattern (entity olmayan URL'leri bulmak için)
URL_PATTERN = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    r'|(?:t\.me/[a-zA-Z0-9_/]+)'
    r'|(?:@[a-zA-Z0-9_]+)'
)

# Markdown link pattern: [text](url) formatını tamamen sil
MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]*)\]\([^)]+\)')

# Telegram message link pattern
TELEGRAM_LINK_PATTERN = re.compile(
    r'(?:https?://)?(?:t\.me|telegram\.me)/(?:c/)?(\d+|[a-zA-Z][a-zA-Z0-9_]*)/(\d+)'
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


def create_entity_copy(entity):
    """
    Entity'yi yeni bir obje olarak kopyala.
    Telethon entity'leri için deep copy düzgün çalışmayabilir.
    """
    if isinstance(entity, MessageEntityBold):
        return MessageEntityBold(offset=entity.offset, length=entity.length)
    elif isinstance(entity, MessageEntityItalic):
        return MessageEntityItalic(offset=entity.offset, length=entity.length)
    elif isinstance(entity, MessageEntityCode):
        return MessageEntityCode(offset=entity.offset, length=entity.length)
    elif isinstance(entity, MessageEntityPre):
        return MessageEntityPre(offset=entity.offset, length=entity.length, language=getattr(entity, 'language', ''))
    elif isinstance(entity, MessageEntityUnderline):
        return MessageEntityUnderline(offset=entity.offset, length=entity.length)
    elif isinstance(entity, MessageEntityStrike):
        return MessageEntityStrike(offset=entity.offset, length=entity.length)
    elif isinstance(entity, MessageEntitySpoiler):
        return MessageEntitySpoiler(offset=entity.offset, length=entity.length)
    elif isinstance(entity, MessageEntityBlockquote):
        return MessageEntityBlockquote(offset=entity.offset, length=entity.length)
    elif isinstance(entity, MessageEntityCustomEmoji):
        return MessageEntityCustomEmoji(offset=entity.offset, length=entity.length, document_id=entity.document_id)
    else:
        # Bilinmeyen entity tipini olduğu gibi döndür
        return entity


def remove_links_from_text(text: str, entities: list) -> tuple:
    """
    Metinden linkleri tamamen kaldır ama formatting entity'lerini koru.
    Returns: (cleaned_text, cleaned_entities)

    Formatting entity tipleri (korunacak):
    - MessageEntityBold, MessageEntityItalic, MessageEntityCode
    - MessageEntityPre, MessageEntityUnderline, MessageEntityStrike
    - MessageEntitySpoiler, MessageEntityCustomEmoji, MessageEntityBlockquote

    Link entity tipleri (tamamen kaldırılacak - hem metin hem URL):
    - MessageEntityTextUrl (link metni + URL tamamen silinecek)
    - MessageEntityUrl (URL silinecek)
    - MessageEntityMention (@mention silinecek)
    """
    if not text:
        return text, []

    if not entities:
        # Entity yok, sadece regex ile URL'leri ve markdown linkleri temizle
        cleaned = URL_PATTERN.sub('', text)
        cleaned = MARKDOWN_LINK_PATTERN.sub('', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        return cleaned.strip(), []

    # Link entity'lerinin kapladığı aralıkları bul (tamamen silinecek)
    link_ranges = []
    formatting_entities = []

    # Link olmayan entity tipleri (korunacak)
    FORMATTING_TYPES = (
        MessageEntityBold, MessageEntityItalic, MessageEntityCode,
        MessageEntityPre, MessageEntityUnderline, MessageEntityStrike,
        MessageEntitySpoiler, MessageEntityCustomEmoji, MessageEntityBlockquote
    )

    for entity in entities:
        if isinstance(entity, (MessageEntityTextUrl, MessageEntityUrl, MessageEntityMention)):
            # Link entity - tamamen sil (hem metin hem URL)
            link_ranges.append((entity.offset, entity.offset + entity.length))
        elif isinstance(entity, FORMATTING_TYPES):
            # Formatting entity - yeni obje olarak kopyala
            formatting_entities.append(create_entity_copy(entity))
        else:
            # Diğer entity'leri de koru (bilinmeyen tipler)
            if not isinstance(entity, (MessageEntityTextUrl, MessageEntityUrl, MessageEntityMention)):
                formatting_entities.append(entity)

    # Link yoksa entity'leri olduğu gibi döndür (regex KULLANMA - offset bozulur!)
    if not link_ranges:
        return text, formatting_entities

    # Aralıkları sırala (sondan başa doğru silmek için ters sırala)
    link_ranges.sort(key=lambda x: x[0], reverse=True)

    # UTF-16 ile çalış (Telegram entity offset'leri UTF-16 code units)
    # Python string'i UTF-16-LE byte array'e çevir
    text_utf16 = text.encode('utf-16-le')

    for start, end in link_ranges:
        removed_length = end - start

        # UTF-16 byte offset'leri (her karakter 2 byte)
        start_byte = start * 2
        end_byte = end * 2

        if start_byte <= len(text_utf16) and end_byte <= len(text_utf16):
            # Metni kes
            text_utf16 = text_utf16[:start_byte] + text_utf16[end_byte:]

            # Formatting entity'lerinin offset'lerini güncelle
            updated_entities = []
            for entity in formatting_entities:
                entity_start = entity.offset
                entity_end = entity.offset + entity.length

                if entity_start >= end:
                    # Entity tamamen silinen kısımdan sonra - offset'i azalt
                    entity.offset -= removed_length
                    updated_entities.append(entity)
                elif entity_end <= start:
                    # Entity tamamen silinen kısımdan önce - değişiklik yok
                    updated_entities.append(entity)
                elif entity_start < start and entity_end > end:
                    # Entity silinen kısmı tamamen kapsıyor - length'i azalt
                    entity.length -= removed_length
                    if entity.length > 0:
                        updated_entities.append(entity)
                elif entity_start >= start and entity_end <= end:
                    # Entity tamamen silinen kısımda - entity'yi atla (sil)
                    pass
                elif entity_start < start and entity_end > start and entity_end <= end:
                    # Entity'nin sonu silinen kısımda
                    entity.length = start - entity_start
                    if entity.length > 0:
                        updated_entities.append(entity)
                elif entity_start >= start and entity_start < end and entity_end > end:
                    # Entity'nin başı silinen kısımda
                    new_length = entity_end - end
                    entity.offset = start
                    entity.length = new_length
                    if entity.length > 0:
                        updated_entities.append(entity)

            formatting_entities = updated_entities

    # UTF-16 byte array'i tekrar string'e çevir
    current_text = text_utf16.decode('utf-16-le', errors='ignore')

    return current_text.strip(), formatting_entities


def append_link_to_text(text: str, link: str) -> str:
    """Append link to the end of text"""
    if not link:
        return text
    if text:
        return f"{text}\n\n{link}"
    return link


async def parse_telegram_link(link: str) -> tuple:
    """Parse telegram message link and return (chat_id, message_id)"""
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
    """Check if the message contains any trigger keywords"""
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
    """Forward a message to target channel with processing"""
    global client

    try:
        target_chat_id = source_channel_config['target_chat_id']
        append_link = source_channel_config['append_link']
        remove_links = source_channel_config['remove_links']
        trigger_keywords = source_channel_config.get('trigger_keywords', '')
        send_link_back = source_channel_config.get('send_link_back', False)

        # Orijinal metin ve entity'leri al
        original_text = message.text or message.caption or ''
        original_entities = message.entities or message.caption_entities or []

        # Trigger keywords kontrolü
        if not check_trigger_keywords(original_text, trigger_keywords):
            return False

        # Link kaldırma işlemi
        if remove_links:
            # Linkleri kaldır ama formatting entity'lerini koru
            final_text, final_entities = remove_links_from_text(original_text, original_entities)
            # Boş liste yerine None kullan
            if not final_entities:
                final_entities = None
        else:
            # Link kaldırma kapalı - orijinali aynen kullan (deep copy ile)
            final_text = original_text
            final_entities = copy.deepcopy(original_entities) if original_entities else None

        # Append link
        if append_link:
            final_text = append_link_to_text(final_text, append_link)

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

        # Mesajı gönder - her zaman entity'leri kullan, parse_mode kullanma
        # Bu sayede markdown parse sorunları olmaz ve formatlar korunur

        if has_media:
            sent_message = await client.send_file(
                entity=target_chat_id,
                file=message.media,
                caption=final_text if final_text else None,
                formatting_entities=final_entities if final_entities else None,
                parse_mode=None
            )
        else:
            sent_message = await client.send_message(
                entity=target_chat_id,
                message=final_text,
                formatting_entities=final_entities if final_entities else None,
                parse_mode=None,
                link_preview=False
            )

        # Source link oluştur - username varsa onu kullan
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

        # Target link oluştur - username varsa onu kullan
        target_link = None
        try:
            target_entity = await client.get_entity(target_chat_id)
            target_username = getattr(target_entity, 'username', None)
            if target_username:
                # Public channel - username ile link
                target_link = f"https://t.me/{target_username}/{sent_message.id}"
            elif str(target_chat_id).startswith('-100'):
                # Private channel - /c/ formatı
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
    """Handle a telegram message link - fetch and forward"""
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
    """Setup the message handler for the client"""
    global client

    @client.on(events.NewMessage)
    async def message_handler(event):
        """Handle new messages in monitored channels/groups"""
        try:
            if not await db.is_bot_enabled():
                return

            source_channel = await db.get_source_channel(event.chat_id)

            if not source_channel:
                return

            message_text = event.message.text or event.message.caption or ''
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
    """Update bot status in database"""
    try:
        await db.set_setting('bot_status', status)
    except Exception:
        pass


async def heartbeat():
    """Periodic heartbeat to update bot status"""
    global shutdown_flag

    while not shutdown_flag:
        try:
            await update_bot_status('online')
        except Exception:
            pass

        await asyncio.sleep(config.HEARTBEAT_INTERVAL)


async def graceful_shutdown(sig=None):
    """Handle graceful shutdown"""
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
    """Setup signal handlers for graceful shutdown"""
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(graceful_shutdown(s))
            )
        except NotImplementedError:
            signal.signal(sig, lambda s, f: asyncio.create_task(graceful_shutdown()))


async def start_client():
    """Start the Telegram client with StringSession"""
    global client

    await client.connect()

    if not await client.is_user_authorized():
        logger.error("Session expired! Run: python generate_session.py")
        raise AuthKeyUnregisteredError("Session expired or invalid")

    return client


async def main():
    """Main function"""
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
