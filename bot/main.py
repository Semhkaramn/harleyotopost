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

# URL regex pattern
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


def remove_urls_from_text(text: str) -> str:
    """Remove all URLs from text"""
    if not text:
        return text
    return URL_PATTERN.sub('', text).strip()


def remove_emojis_from_text(text: str) -> str:
    """Remove emojis from text"""
    if not text:
        return text
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text).strip()


def clean_message_text(text: str, remove_links: bool, remove_emojis: bool) -> str:
    """Clean message text based on settings"""
    if not text:
        return text

    result = text

    if remove_links:
        result = remove_urls_from_text(result)

    if remove_emojis:
        result = remove_emojis_from_text(result)

    # Clean up extra whitespace and newlines
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = re.sub(r' {2,}', ' ', result)

    return result.strip()


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

    # If it's a numeric ID (private channel/group)
    if chat_identifier.isdigit():
        chat_id = int(f"-100{chat_identifier}")
    else:
        # It's a username
        chat_id = chat_identifier

    return chat_id, message_id


def check_trigger_keywords(text: str, keywords_str: str) -> bool:
    """Check if the message contains any trigger keywords"""
    if not keywords_str or not keywords_str.strip():
        # No keywords set, allow all messages
        return True

    if not text:
        return False

    text_lower = text.lower()
    # Keywords are comma-separated
    keywords = [kw.strip().lower() for kw in keywords_str.split(',') if kw.strip()]

    if not keywords:
        return True

    # Check if any keyword exists in the text
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
        remove_emojis_flag = source_channel_config['remove_emojis']
        trigger_keywords = source_channel_config.get('trigger_keywords', '')
        send_link_back = source_channel_config.get('send_link_back', False)

        # Clean the message text
        original_text = message.text or message.caption or ''

        # Check trigger keywords
        if not check_trigger_keywords(original_text, trigger_keywords):
            logger.info(f"Message {message.id} skipped - no matching trigger keywords")
            return False

        cleaned_text = clean_message_text(original_text, remove_links, remove_emojis_flag)
        final_text = append_link_to_text(cleaned_text, append_link)

        # Determine media type
        has_media = message.media is not None
        media_type = None

        if has_media:
            if isinstance(message.media, MessageMediaPhoto):
                media_type = 'photo'
            elif isinstance(message.media, MessageMediaDocument):
                media_type = 'document'
            else:
                media_type = 'other'

        # Send to target
        if has_media:
            # Forward with media
            sent_message = await client.send_file(
                target_chat_id,
                message.media,
                caption=final_text if final_text else None,
                parse_mode='html'
            )
        else:
            # Text only
            sent_message = await client.send_message(
                target_chat_id,
                final_text,
                parse_mode='html'
            )

        # Create source link
        source_chat_id = message.chat_id
        if str(source_chat_id).startswith('-100'):
            source_link = f"t.me/c/{str(source_chat_id)[4:]}/{message.id}"
        else:
            source_link = f"t.me/{source_chat_id}/{message.id}"

        # Create target message link
        target_link = None
        if str(target_chat_id).startswith('-100'):
            target_link = f"https://t.me/c/{str(target_chat_id)[4:]}/{sent_message.id}"
        else:
            target_link = f"https://t.me/{target_chat_id}/{sent_message.id}"

        # Send link back to source channel if enabled
        if send_link_back and source_event_chat_id and target_link:
            try:
                await client.send_message(
                    source_event_chat_id,
                    target_link
                )
                logger.info(f"Sent target link back to {source_event_chat_id}")
            except Exception as e:
                logger.warning(f"Could not send link back: {e}")

        # Log to database
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

        logger.info(f"Forwarded message {message.id} from {source_chat_id} to {target_chat_id}")
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
        return False


async def handle_telegram_link(event, link: str):
    """Handle a telegram message link - fetch and forward"""
    global client

    try:
        chat_id, message_id = await parse_telegram_link(link)

        if not chat_id or not message_id:
            logger.warning(f"Could not parse link: {link}")
            return

        # Get the original message
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

        # Get source channel config from where the link was posted
        source_channel = await db.get_source_channel(event.chat_id)

        if not source_channel:
            logger.warning(f"No config for source channel {event.chat_id}")
            return

        # Check daily limit
        can_post = await db.can_post_today(source_channel['id'])
        if not can_post:
            remaining = await db.get_remaining_posts_today(source_channel['id'])
            logger.info(f"Daily limit reached for channel {source_channel['id']}. Remaining: {remaining}")
            return

        # Forward the message (pass source event chat_id for link back feature)
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
            # Check if bot is enabled
            if not await db.is_bot_enabled():
                return

            # Check if this is a source channel
            source_channel = await db.get_source_channel(event.chat_id)

            if not source_channel:
                return

            message_text = event.message.text or event.message.caption or ''
            listen_type = source_channel.get('listen_type', 'direct')

            # Handle based on listen type
            if listen_type == 'link':
                # Only process telegram links in the message
                links = TELEGRAM_LINK_PATTERN.findall(message_text)

                if links:
                    # Reconstruct full links and process each
                    for match in TELEGRAM_LINK_PATTERN.finditer(message_text):
                        full_link = match.group(0)
                        await handle_telegram_link(event, full_link)
                # If no links and listen_type is 'link', ignore the message

            else:  # listen_type == 'direct'
                # Check for telegram links in the message first
                links = TELEGRAM_LINK_PATTERN.findall(message_text)

                if links:
                    # If there are links, process them
                    for match in TELEGRAM_LINK_PATTERN.finditer(message_text):
                        full_link = match.group(0)
                        await handle_telegram_link(event, full_link)
                else:
                    # No links - forward the message directly if it has content
                    if message_text or event.message.media:
                        # Check daily limit
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

    # Update status to offline
    try:
        await update_bot_status('offline')
    except Exception:
        pass

    # Disconnect client
    if client and client.is_connected():
        try:
            await client.disconnect()
            logger.info("Telegram client disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting client: {e}")

    # Close database connection
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
            # Windows doesn't support add_signal_handler
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

    # Validate configuration
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

    # Initialize database
    try:
        await db.init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Create and start client
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

    # Get user info
    try:
        me = await client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username or 'no username'})")
    except Exception as e:
        logger.warning(f"Could not get user info: {e}")

    # Setup message handler
    await setup_message_handler()
    logger.info("Message handler registered")

    # Update status
    await update_bot_status('online')

    # Start heartbeat
    heartbeat_task = asyncio.create_task(heartbeat())

    # Get monitored channels
    try:
        channels = await db.get_active_source_channels()
        logger.info(f"Monitoring {len(channels)} channels")

        for channel in channels:
            logger.info(f"  - {channel['source_title'] or channel['source_chat_id']}")
    except Exception as e:
        logger.warning(f"Could not get channel list: {e}")

    logger.info("Bot is running...")
    logger.info("=" * 50)

    # Run until disconnected or shutdown
    try:
        await client.run_until_disconnected()
    except Exception as e:
        if not shutdown_flag:
            logger.error(f"Client disconnected unexpectedly: {e}")

    # Cleanup
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Setup signal handlers
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
