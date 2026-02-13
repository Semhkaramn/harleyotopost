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


def remove_links_from_text(text: str, entities: list) -> str:
    """
    Metinden linkleri kaldır.
    Entity'lerdeki TextUrl, Url, Mention'ların kapladığı metinleri sil.
    Ayrıca regex ile bulunan URL'leri de sil.
    """
    if not text:
        return text

    if not entities:
        # Entity yok, sadece regex ile URL'leri temizle
        cleaned = URL_PATTERN.sub('', text)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        return cleaned.strip()

    # Link entity'lerinin kapladığı aralıkları bul (byte pozisyonları)
    # Telegram UTF-16 kullanıyor
    removal_ranges = []

    for entity in entities:
        if isinstance(entity, (MessageEntityTextUrl, MessageEntityUrl, MessageEntityMention)):
            # UTF-16 offset'leri byte pozisyonuna çevir
            removal_ranges.append((entity.offset, entity.offset + entity.length))

    # Aralıkları sırala (sondan başa doğru silmek için ters sırala)
    removal_ranges.sort(key=lambda x: x[0], reverse=True)

    # Metni UTF-16 olarak encode et
    text_utf16 = text.encode('utf-16-le')

    # Her aralığı sil (sondan başa)
    for start, end in removal_ranges:
        start_byte = start * 2
        end_byte = end * 2
        if start_byte < len(text_utf16) and end_byte <= len(text_utf16):
            text_utf16 = text_utf16[:start_byte] + text_utf16[end_byte:]

    # Geri decode et
    new_text = text_utf16.decode('utf-16-le', errors='ignore')

    # Regex ile kalan URL'leri de temizle
    new_text = URL_PATTERN.sub('', new_text)

    # Temizlik
    new_text = re.sub(r'\n{3,}', '\n\n', new_text)
    new_text = re.sub(r' {2,}', ' ', new_text)

    return new_text.strip()


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
            # Linkleri kaldır, entity kullanma (düz metin olarak gönder)
            final_text = remove_links_from_text(original_text, original_entities)
            final_entities = None  # Entity kullanma
            logger.info(f"Links removed - original: {len(original_text)} chars, final: {len(final_text)} chars")
        else:
            # Link kaldırma kapalı - orijinali aynen kullan
            final_text = original_text
            final_entities = original_entities

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

        # Source link oluştur
        source_chat_id = message.chat_id
        if str(source_chat_id).startswith('-100'):
            source_link = f"t.me/c/{str(source_chat_id)[4:]}/{message.id}"
        else:
            source_link = f"t.me/{source_chat_id}/{message.id}"

        # Target link oluştur
        target_link = None
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
                links = TELEGRAM_LINK_PATTERN.findall(message_text)

                if links:
                    for match in TELEGRAM_LINK_PATTERN.finditer(message_text):
                        full_link = match.group(0)
                        await handle_telegram_link(event, full_link)

            else:  # listen_type == 'direct'
                links = TELEGRAM_LINK_PATTERN.findall(message_text)

                if links:
                    for match in TELEGRAM_LINK_PATTERN.finditer(message_text):
                        full_link = match.group(0)
                        await handle_telegram_link(event, full_link)
                else:
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
