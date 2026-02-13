import asyncio
import re
import logging
from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageEntityTextUrl,
    MessageEntityUrl,
    InputMediaPhoto,
    InputMediaDocument
)
from telethon.errors import FloodWaitError, ChatWriteForbiddenError
import config
import database as db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Initialize client
client = TelegramClient(
    config.SESSION_NAME,
    config.API_ID,
    config.API_HASH
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


async def forward_message(source_channel_config: dict, message):
    """Forward a message to target channel with processing"""
    try:
        target_chat_id = source_channel_config['target_chat_id']
        append_link = source_channel_config['append_link']
        remove_links = source_channel_config['remove_links']
        remove_emojis_flag = source_channel_config['remove_emojis']

        # Clean the message text
        original_text = message.text or message.caption or ''
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

        # Forward the message
        await forward_message(source_channel, message)

    except Exception as e:
        logger.error(f"Error handling telegram link: {e}")


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

        # Check for telegram links in the message
        links = TELEGRAM_LINK_PATTERN.findall(message_text)

        if links:
            # Reconstruct full links and process each
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

                await forward_message(source_channel, event.message)

    except Exception as e:
        logger.error(f"Error in message handler: {e}")


async def update_bot_status(status: str):
    """Update bot status in database"""
    await db.set_setting('bot_status', status)
    await db.set_setting('last_heartbeat', str(asyncio.get_event_loop().time()))


async def heartbeat():
    """Periodic heartbeat to update bot status"""
    while True:
        try:
            await update_bot_status('online')
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
        await asyncio.sleep(30)


async def main():
    """Main function"""
    logger.info("Starting Telegram Forwarder Bot...")

    # Initialize database
    await db.init_db()
    logger.info("Database initialized")

    # Start the client
    await client.start(phone=config.PHONE_NUMBER)
    logger.info("Telegram client started")

    # Update status
    await update_bot_status('online')

    # Start heartbeat
    asyncio.create_task(heartbeat())

    # Get monitored channels
    channels = await db.get_active_source_channels()
    logger.info(f"Monitoring {len(channels)} channels")

    for channel in channels:
        logger.info(f"  - {channel['source_title'] or channel['source_chat_id']}")

    # Run until disconnected
    logger.info("Bot is running...")
    await client.run_until_disconnected()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
