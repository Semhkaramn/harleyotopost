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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

# Telegram message link pattern
TELEGRAM_LINK_PATTERN = re.compile(
    r'(?:https?://)?(?:t\.me|telegram\.me)/(?:c/)?(\d+|[a-zA-Z][a-zA-Z0-9_]*)/(\d+)'
)


def create_client():
    """Create Telegram client with StringSession"""
    if not config.SESSION_STRING:
        logger.error("SESSION_STRING is required!")
        logger.error("Run: python generate_session.py to create one")
        sys.exit(1)

    logger.info("Using StringSession")
    session = StringSession(config.SESSION_STRING)

    return TelegramClient(
        session,
        config.API_ID,
        config.API_HASH,
        connection_retries=5,
        retry_delay=1,
        auto_reconnect=True
    )


def remove_links_from_text(text: str, entities: list) -> tuple:
    """
    Metinden linkleri kaldır ama formatting entity'lerini koru.
    Returns: (cleaned_text, cleaned_entities)

    Formatting entity tipleri (korunacak):
    - MessageEntityBold, MessageEntityItalic, MessageEntityCode
    - MessageEntityPre, MessageEntityUnderline, MessageEntityStrike
    - MessageEntitySpoiler, MessageEntityCustomEmoji, MessageEntityBlockquote

    Link entity tipleri (kaldırılacak):
    - MessageEntityTextUrl, MessageEntityUrl, MessageEntityMention
    """
    if not text:
        return text, []

    if not entities:
        # Entity yok, sadece regex ile URL'leri temizle
        cleaned = URL_PATTERN.sub('', text)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        return cleaned.strip(), []

    # Deep copy ile entity'leri kopyala (orijinalleri değiştirmemek için)
    entities_copy = copy.deepcopy(entities)

    # Link entity'lerinin kapladığı aralıkları bul
    link_ranges = []
    formatting_entities = []

    # Link olmayan entity tipleri
    FORMATTING_TYPES = (
        MessageEntityBold, MessageEntityItalic, MessageEntityCode,
        MessageEntityPre, MessageEntityUnderline, MessageEntityStrike,
        MessageEntitySpoiler, MessageEntityCustomEmoji, MessageEntityBlockquote
    )

    for entity in entities_copy:
        if isinstance(entity, (MessageEntityTextUrl, MessageEntityUrl, MessageEntityMention)):
            link_ranges.append((entity.offset, entity.offset + entity.length))
        elif isinstance(entity, FORMATTING_TYPES):
            # Formatting entity'lerini koru
            formatting_entities.append(entity)
        # Diğer bilinmeyen entity'leri de koru
        elif not isinstance(entity, (MessageEntityTextUrl, MessageEntityUrl, MessageEntityMention)):
            formatting_entities.append(entity)

    if not link_ranges:
        # Link yok, regex ile temizle
        # NOT: Regex temizliği entity offset'lerini bozabilir, dikkatli ol
        new_text = text
        # Sadece entity ile kapsanmayan URL'leri temizle
        # Bu durumda entity'lerin bozulmaması için regex temizliğini atla
        new_text = re.sub(r'\n{3,}', '\n\n', new_text)
        new_text = re.sub(r' {2,}', ' ', new_text)
        return new_text.strip(), formatting_entities

    # Aralıkları sırala (sondan başa doğru silmek için ters sırala)
    link_ranges.sort(key=lambda x: x[0], reverse=True)

    # Her aralığı sil ve entity offset'lerini güncelle
    # UTF-16 code units olarak çalış (Telegram entity offset'leri UTF-16 kullanır)
    current_text = text

    for start, end in link_ranges:
        removed_length = end - start

        # UTF-16 offset'leri Python string index'lerine çevir
        text_utf16 = current_text.encode('utf-16-le')
        start_byte = start * 2
        end_byte = end * 2

        if start_byte <= len(text_utf16) and end_byte <= len(text_utf16):
            # Metni kes
            text_utf16 = text_utf16[:start_byte] + text_utf16[end_byte:]
            current_text = text_utf16.decode('utf-16-le', errors='ignore')

            # Formatting entity'lerinin offset'lerini güncelle
            new_formatting_entities = []
            for entity in formatting_entities:
                entity_end = entity.offset + entity.length

                if entity.offset >= end:
                    # Entity tamamen silinen kısımdan sonra, offset'i azalt
                    entity.offset -= removed_length
                    new_formatting_entities.append(entity)
                elif entity_end <= start:
                    # Entity tamamen silinen kısımdan önce, değişiklik yok
                    new_formatting_entities.append(entity)
                elif entity.offset < start and entity_end > end:
                    # Entity silinen kısmı tamamen kapsıyor, length'i azalt
                    entity.length -= removed_length
                    new_formatting_entities.append(entity)
                elif entity.offset >= start and entity_end <= end:
                    # Entity tamamen silinen kısımda, entity'yi atla
                    pass
                elif entity.offset < start and entity_end > start and entity_end <= end:
                    # Entity'nin sonu silinen kısımda
                    entity.length = start - entity.offset
                    if entity.length > 0:
                        new_formatting_entities.append(entity)
                elif entity.offset >= start and entity.offset < end and entity_end > end:
                    # Entity'nin başı silinen kısımda
                    new_length = entity_end - end
                    entity.offset = start
                    entity.length = new_length
                    if entity.length > 0:
                        new_formatting_entities.append(entity)

            formatting_entities = new_formatting_entities

    # Temizlik
    current_text = re.sub(r'\n{3,}', '\n\n', current_text)
    current_text = re.sub(r' {2,}', ' ', current_text)

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
            logger.info(f"Message {message.id} skipped - no matching trigger keywords")
            return False

        # Link kaldırma işlemi
        if remove_links:
            # Linkleri kaldır ama formatting entity'lerini koru
            final_text, final_entities = remove_links_from_text(original_text, original_entities)
            # Boş liste yerine None kullan
            if not final_entities:
                final_entities = None
            logger.info(f"Links removed - original: {len(original_text)} chars, final: {len(final_text)} chars, entities kept: {len(final_entities) if final_entities else 0}")
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

        # Mesajı gönder
        if has_media:
            sent_message = await client.send_file(
                entity=target_chat_id,
                file=message.media,
                caption=final_text if final_text else None,
                formatting_entities=final_entities,
                parse_mode=None
            )
        else:
            sent_message = await client.send_message(
                entity=target_chat_id,
                message=final_text,
                formatting_entities=final_entities,
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
        except Exception as e:
            logger.warning(f"Could not get source entity for link: {e}")
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
        except Exception as e:
            logger.warning(f"Could not get target entity for link: {e}")
            if str(target_chat_id).startswith('-100'):
                target_link = f"https://t.me/c/{str(target_chat_id)[4:]}/{sent_message.id}"
            else:
                target_link = f"https://t.me/{target_chat_id}/{sent_message.id}"

        # Send link back
        if send_link_back and source_event_chat_id and target_link:
            try:
                await client.send_message(source_event_chat_id, target_link)
                logger.info(f"Sent target link back to {source_event_chat_id}")
            except Exception as e:
                logger.warning(f"Could not send link back: {e}")

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

        logger.info(f"✅ Forwarded message {message.id} from {source_chat_id} to {target_chat_id}")
        return True

    except FloodWaitError as e:
        logger.warning(f"Flood wait: {e.seconds} seconds")
        await asyncio.sleep(e.seconds)
        return False

    except ChatWriteForbiddenError:
        logger.error(f"Cannot write to target chat {target_chat_id}")
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
        logger.error(f"Error forwarding message: {e}")
        import traceback
        traceback.print_exc()
        return False


async def handle_telegram_link(event, link: str):
    """Handle a telegram message link - fetch and forward"""
    global client

    try:
        chat_id, message_id = await parse_telegram_link(link)

        if not chat_id or not message_id:
            logger.warning(f"Could not parse link: {link}")
            return

        try:
            if isinstance(chat_id, str):
                entity = await client.get_entity(chat_id)
                message = await client.get_messages(entity, ids=message_id)
            else:
                message = await client.get_messages(chat_id, ids=message_id)
        except Exception as e:
            logger.error(f"Could not fetch message from {chat_id}/{message_id}: {e}")
            return

        if not message:
            logger.warning(f"Message not found: {link}")
            return

        source_channel = await db.get_source_channel(event.chat_id)

        if not source_channel:
            logger.warning(f"No config for source channel {event.chat_id}")
            return

        can_post = await db.can_post_today(source_channel['id'])
        if not can_post:
            remaining = await db.get_remaining_posts_today(source_channel['id'])
            logger.info(f"Daily limit reached for channel {source_channel['id']}. Remaining: {remaining}")
            return

        await forward_message(source_channel, message, source_event_chat_id=event.chat_id)

    except Exception as e:
        logger.error(f"Error handling telegram link: {e}")


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
                # LINK MODU: Mesajdaki linkleri bul, o linklerdeki mesajları çek ve gönder
                links = TELEGRAM_LINK_PATTERN.findall(message_text)

                if links:
                    for match in TELEGRAM_LINK_PATTERN.finditer(message_text):
                        full_link = match.group(0)
                        await handle_telegram_link(event, full_link)

            else:  # listen_type == 'direct'
                # DIRECT MODU: Gelen mesajı direkt al ve gönder (entity'ler korunur)
                if message_text or event.message.media:
                    can_post = await db.can_post_today(source_channel['id'])
                    if not can_post:
                        logger.info(f"Daily limit reached for channel {source_channel['id']}")
                        return

                    await forward_message(source_channel, event.message, source_event_chat_id=event.chat_id)

        except Exception as e:
            logger.error(f"Error in message handler: {e}")


async def update_bot_status(status: str):
    """Update bot status in database"""
    try:
        await db.set_setting('bot_status', status)
    except Exception as e:
        logger.error(f"Error updating bot status: {e}")


async def heartbeat():
    """Periodic heartbeat to update bot status"""
    global shutdown_flag

    while not shutdown_flag:
        try:
            await update_bot_status('online')
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

        await asyncio.sleep(config.HEARTBEAT_INTERVAL)


async def graceful_shutdown(sig=None):
    """Handle graceful shutdown"""
    global shutdown_flag, client

    if sig:
        logger.info(f"Received signal {sig.name}, shutting down...")
    else:
        logger.info("Shutting down...")

    shutdown_flag = True

    try:
        await update_bot_status('offline')
    except Exception:
        pass

    if client and client.is_connected():
        try:
            await client.disconnect()
            logger.info("Telegram client disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting client: {e}")

    try:
        await db.close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


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

    logger.info("Connecting with StringSession...")
    await client.connect()

    if not await client.is_user_authorized():
        logger.error("Session is not authorized! Please generate a new session string.")
        logger.error("Run: python generate_session.py")
        raise AuthKeyUnregisteredError("Session expired or invalid")

    logger.info("Successfully connected with StringSession")
    return client


async def main():
    """Main function"""
    global client, shutdown_flag

    logger.info("=" * 50)
    logger.info("Starting Telegram Forwarder Bot...")
    logger.info("=" * 50)

    if not config.API_ID or not config.API_HASH:
        logger.error("API_ID and API_HASH are required!")
        logger.error("Get them from https://my.telegram.org")
        sys.exit(1)

    if not config.DATABASE_URL:
        logger.error("DATABASE_URL is required!")
        sys.exit(1)

    if not config.SESSION_STRING:
        logger.error("SESSION_STRING is required!")
        logger.error("Run: python generate_session.py to create one")
        sys.exit(1)

    try:
        await db.init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    client = create_client()

    try:
        await start_client()
    except (AuthKeyUnregisteredError, UserDeactivatedBanError) as e:
        logger.error(f"Authentication failed: {e}")
        logger.error("Please generate a new session string with generate_session.py")
        await db.close_db()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start client: {e}")
        await db.close_db()
        sys.exit(1)

    try:
        me = await client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username or 'no username'})")
    except Exception as e:
        logger.warning(f"Could not get user info: {e}")

    await setup_message_handler()
    logger.info("Message handler registered")

    await update_bot_status('online')

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        channels = await db.get_active_source_channels()
        logger.info(f"Monitoring {len(channels)} channels")

        for channel in channels:
            logger.info(f"  - {channel['source_title'] or channel['source_chat_id']}")
    except Exception as e:
        logger.warning(f"Could not get channel list: {e}")

    logger.info("Bot is running...")
    logger.info("=" * 50)

    try:
        await client.run_until_disconnected()
    except Exception as e:
        if not shutdown_flag:
            logger.error(f"Client disconnected unexpectedly: {e}")

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
        logger.info("Bot stopped by user")
        loop.run_until_complete(graceful_shutdown())
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        loop.run_until_complete(graceful_shutdown())
    finally:
        loop.close()
