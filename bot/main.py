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
    MessageEntityStrike,
    MessageEntityUnderline,
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


def utf16_len(text: str) -> int:
    """Get UTF-16 length of text (Telegram uses UTF-16 for entity offsets)"""
    return len(text.encode('utf-16-le')) // 2


def utf16_to_utf8_offset(text: str, utf16_offset: int) -> int:
    """Convert UTF-16 offset to UTF-8 string index"""
    encoded = text.encode('utf-16-le')
    # Each UTF-16 code unit is 2 bytes
    byte_offset = utf16_offset * 2
    if byte_offset > len(encoded):
        byte_offset = len(encoded)
    decoded = encoded[:byte_offset].decode('utf-16-le', errors='ignore')
    return len(decoded)


def copy_entity(entity):
    """Create a deep copy of an entity"""
    from copy import deepcopy
    return deepcopy(entity)


def clean_message_with_entities(text: str, entities: list, remove_links: bool) -> tuple:
    """
    Clean message text and entities.
    - Removes hyperlinked text (text with attached links) when remove_links is True
    - Removes plain URLs and @mentions when remove_links is True
    - Keeps all formatting (bold, italic, etc.)
    - Keeps all emojis (normal and premium/custom)

    Returns: (cleaned_text, cleaned_entities)
    """
    if not text:
        return text, entities if entities else []

    if not remove_links:
        # Still need to copy entities to avoid mutation
        if entities:
            return text, [copy_entity(e) for e in entities]
        return text, []

    # First, collect ranges to remove from entities
    ranges_to_remove = []  # List of (utf16_start, utf16_end) tuples
    entities_to_keep = []

    if entities:
        for entity in entities:
            # Check if this is a link-related entity
            if isinstance(entity, MessageEntityTextUrl):
                # Hyperlinked text - remove the entire text range
                ranges_to_remove.append((entity.offset, entity.offset + entity.length))
            elif isinstance(entity, MessageEntityUrl):
                # Plain URL in text - remove it
                ranges_to_remove.append((entity.offset, entity.offset + entity.length))
            elif isinstance(entity, MessageEntityMention):
                # @mention - remove it
                ranges_to_remove.append((entity.offset, entity.offset + entity.length))
            else:
                # Keep other entities (bold, italic, emoji, custom emoji, etc.)
                entities_to_keep.append(copy_entity(entity))

    # Also find plain URLs in text that don't have entities
    # Convert text to work with UTF-16 offsets
    for match in URL_PATTERN.finditer(text):
        start_utf8 = match.start()
        end_utf8 = match.end()
        # Convert to UTF-16 offsets
        start_utf16 = utf16_len(text[:start_utf8])
        end_utf16 = start_utf16 + utf16_len(match.group())

        # Check if this range is already covered by an entity
        already_covered = False
        for r_start, r_end in ranges_to_remove:
            if r_start <= start_utf16 and r_end >= end_utf16:
                already_covered = True
                break

        if not already_covered:
            ranges_to_remove.append((start_utf16, end_utf16))

    if not ranges_to_remove:
        # No links to remove, just clean whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', text)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        return cleaned.strip(), entities_to_keep

    # Merge overlapping ranges
    ranges_to_remove.sort(key=lambda x: x[0])
    merged_ranges = []
    for start, end in ranges_to_remove:
        if merged_ranges and start <= merged_ranges[-1][1]:
            merged_ranges[-1] = (merged_ranges[-1][0], max(merged_ranges[-1][1], end))
        else:
            merged_ranges.append((start, end))

    # Sort ranges by start position (descending) to remove from end to start
    merged_ranges.sort(key=lambda x: x[0], reverse=True)

    # Convert text to list of UTF-16 code units for manipulation
    # We'll work with the string directly but track UTF-16 positions
    cleaned_text = text

    # Remove ranges from end to start to maintain correct offsets
    for utf16_start, utf16_end in merged_ranges:
        # Convert UTF-16 offsets to string indices
        str_start = utf16_to_utf8_offset(cleaned_text, utf16_start)
        str_end = utf16_to_utf8_offset(cleaned_text, utf16_end)
        cleaned_text = cleaned_text[:str_start] + cleaned_text[str_end:]

    # Calculate new offsets for kept entities
    # Sort ranges ascending for offset calculation
    sorted_ranges = sorted(merged_ranges, key=lambda x: x[0])

    adjusted_entities = []
    for entity in entities_to_keep:
        original_offset = entity.offset
        original_length = entity.length
        entity_end = original_offset + original_length

        # Calculate shift and check if entity is affected
        shift = 0
        entity_removed = False
        new_length = original_length

        for r_start, r_end in sorted_ranges:
            removed_length = r_end - r_start

            if r_end <= original_offset:
                # Range is completely before entity - shift offset
                shift += removed_length
            elif r_start >= entity_end:
                # Range is completely after entity - no effect
                pass
            elif r_start <= original_offset and r_end >= entity_end:
                # Range completely contains entity - remove it
                entity_removed = True
                break
            elif r_start > original_offset and r_end < entity_end:
                # Range is inside entity - reduce length
                new_length -= removed_length
            elif r_start <= original_offset < r_end < entity_end:
                # Range overlaps start of entity
                overlap = r_end - original_offset
                shift += (r_start - original_offset) if r_start < original_offset else 0
                new_length -= overlap
                entity_removed = True  # Partial removal is tricky, skip
                break
            elif original_offset < r_start < entity_end <= r_end:
                # Range overlaps end of entity
                new_length = r_start - original_offset

        if not entity_removed and new_length > 0:
            entity.offset = original_offset - shift
            entity.length = new_length
            if entity.offset >= 0:
                adjusted_entities.append(entity)

    # Clean up extra whitespace and newlines
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)

    # Handle strip carefully to adjust entity offsets
    if cleaned_text:
        # Count leading whitespace/newlines
        leading_stripped = len(cleaned_text) - len(cleaned_text.lstrip())
        if leading_stripped > 0:
            # Convert to UTF-16 length for offset adjustment
            leading_utf16 = utf16_len(cleaned_text[:leading_stripped])
            # Adjust all entity offsets
            for entity in adjusted_entities:
                entity.offset -= leading_utf16
            cleaned_text = cleaned_text.lstrip()

        # Strip trailing (doesn't affect offsets)
        cleaned_text = cleaned_text.rstrip()

    # Remove entities with negative offsets (they got stripped away)
    adjusted_entities = [e for e in adjusted_entities if e.offset >= 0]

    return cleaned_text, adjusted_entities


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
        trigger_keywords = source_channel_config.get('trigger_keywords', '')
        send_link_back = source_channel_config.get('send_link_back', False)

        # Get original text and entities
        original_text = message.text or message.caption or ''
        original_entities = list(message.entities or message.caption_entities or [])

        # Check trigger keywords
        if not check_trigger_keywords(original_text, trigger_keywords):
            logger.info(f"Message {message.id} skipped - no matching trigger keywords")
            return False

        # Log original entities for debugging
        logger.info(f"Original entities count: {len(original_entities)}")
        for i, ent in enumerate(original_entities):
            logger.debug(f"  Entity {i}: {type(ent).__name__} at {ent.offset}:{ent.length}")

        # Clean text and entities (removes hyperlinked text, URLs, mentions if remove_links is True)
        # Keeps all formatting (bold, italic, etc.) and emojis (normal and premium)
        cleaned_text, cleaned_entities = clean_message_with_entities(original_text, original_entities, remove_links)

        # Log cleaned entities for debugging
        logger.info(f"Cleaned entities count: {len(cleaned_entities)}")
        for i, ent in enumerate(cleaned_entities):
            logger.debug(f"  Entity {i}: {type(ent).__name__} at {ent.offset}:{ent.length}")

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

        # Send to target with entities (preserves formatting and emojis including premium)
        # Important: Only pass entities if there are any, otherwise set to None
        entities_to_send = cleaned_entities if cleaned_entities else None

        if has_media:
            # Forward with media
            sent_message = await client.send_file(
                target_chat_id,
                message.media,
                caption=final_text if final_text else None,
                formatting_entities=entities_to_send
            )
        else:
            # Text only
            sent_message = await client.send_message(
                target_chat_id,
                final_text,
                formatting_entities=entities_to_send
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
