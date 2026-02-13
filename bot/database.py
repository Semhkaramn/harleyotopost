import asyncpg
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import config

pool: Optional[asyncpg.Pool] = None


async def init_db():
    """Initialize database connection pool and create tables"""
    global pool
    pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=1, max_size=10)

    async with pool.acquire() as conn:
        # Global settings table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id SERIAL PRIMARY KEY,
                key VARCHAR(255) UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Source channels/groups with their own settings
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS source_channels (
                id SERIAL PRIMARY KEY,
                source_chat_id BIGINT UNIQUE NOT NULL,
                source_title TEXT,
                source_username TEXT,
                target_chat_id BIGINT NOT NULL,
                target_title TEXT,
                append_link TEXT DEFAULT '',
                daily_limit INTEGER DEFAULT 4,
                remove_links BOOLEAN DEFAULT TRUE,
                remove_emojis BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Posts history
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                source_channel_id INTEGER REFERENCES source_channels(id),
                source_link TEXT NOT NULL,
                source_chat_id BIGINT,
                source_message_id BIGINT,
                target_chat_id BIGINT,
                target_message_id BIGINT,
                message_text TEXT,
                has_media BOOLEAN DEFAULT FALSE,
                media_type TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Daily stats per source channel
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id SERIAL PRIMARY KEY,
                source_channel_id INTEGER REFERENCES source_channels(id),
                date DATE NOT NULL,
                post_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                UNIQUE(source_channel_id, date)
            )
        ''')

        # Initialize default global settings
        default_settings = {
            'bot_enabled': 'true',
            'bot_status': 'offline'
        }

        for key, value in default_settings.items():
            await conn.execute('''
                INSERT INTO settings (key, value) VALUES ($1, $2)
                ON CONFLICT (key) DO NOTHING
            ''', key, value)


async def close_db():
    """Close database connection pool"""
    global pool
    if pool:
        await pool.close()


# ============== GLOBAL SETTINGS ==============

async def get_setting(key: str) -> Optional[str]:
    """Get a global setting value"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT value FROM settings WHERE key = $1', key)
        return row['value'] if row else None


async def set_setting(key: str, value: str):
    """Set a global setting value"""
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO settings (key, value, updated_at) VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
        ''', key, value)


async def get_all_settings() -> Dict[str, str]:
    """Get all global settings"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT key, value FROM settings')
        return {row['key']: row['value'] for row in rows}


async def is_bot_enabled() -> bool:
    """Check if bot is enabled"""
    val = await get_setting('bot_enabled')
    return val == 'true'


# ============== SOURCE CHANNELS ==============

async def add_source_channel(
    source_chat_id: int,
    target_chat_id: int,
    source_title: str = None,
    source_username: str = None,
    target_title: str = None,
    append_link: str = '',
    daily_limit: int = 4,
    remove_links: bool = True,
    remove_emojis: bool = False
) -> int:
    """Add or update a source channel configuration"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO source_channels
            (source_chat_id, target_chat_id, source_title, source_username,
             target_title, append_link, daily_limit, remove_links, remove_emojis)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (source_chat_id) DO UPDATE SET
                target_chat_id = $2,
                source_title = COALESCE($3, source_channels.source_title),
                source_username = COALESCE($4, source_channels.source_username),
                target_title = COALESCE($5, source_channels.target_title),
                append_link = $6,
                daily_limit = $7,
                remove_links = $8,
                remove_emojis = $9,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        ''', source_chat_id, target_chat_id, source_title, source_username,
            target_title, append_link, daily_limit, remove_links, remove_emojis)
        return row['id']


async def update_source_channel(
    source_chat_id: int,
    target_chat_id: int = None,
    append_link: str = None,
    daily_limit: int = None,
    remove_links: bool = None,
    remove_emojis: bool = None,
    is_active: bool = None
):
    """Update source channel settings"""
    async with pool.acquire() as conn:
        updates = []
        values = [source_chat_id]
        idx = 2

        if target_chat_id is not None:
            updates.append(f"target_chat_id = ${idx}")
            values.append(target_chat_id)
            idx += 1
        if append_link is not None:
            updates.append(f"append_link = ${idx}")
            values.append(append_link)
            idx += 1
        if daily_limit is not None:
            updates.append(f"daily_limit = ${idx}")
            values.append(daily_limit)
            idx += 1
        if remove_links is not None:
            updates.append(f"remove_links = ${idx}")
            values.append(remove_links)
            idx += 1
        if remove_emojis is not None:
            updates.append(f"remove_emojis = ${idx}")
            values.append(remove_emojis)
            idx += 1
        if is_active is not None:
            updates.append(f"is_active = ${idx}")
            values.append(is_active)
            idx += 1

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE source_channels SET {', '.join(updates)} WHERE source_chat_id = $1"
            await conn.execute(query, *values)


async def remove_source_channel(source_chat_id: int):
    """Remove a source channel"""
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM source_channels WHERE source_chat_id = $1', source_chat_id)


async def get_source_channel(source_chat_id: int) -> Optional[Dict[str, Any]]:
    """Get a source channel by chat ID"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT * FROM source_channels WHERE source_chat_id = $1 AND is_active = TRUE',
            source_chat_id
        )
        return dict(row) if row else None


async def get_all_source_channels() -> List[Dict[str, Any]]:
    """Get all source channels"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM source_channels ORDER BY created_at DESC')
        return [dict(row) for row in rows]


async def get_active_source_channels() -> List[Dict[str, Any]]:
    """Get all active source channels"""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM source_channels WHERE is_active = TRUE')
        return [dict(row) for row in rows]


async def is_source_channel(chat_id: int) -> bool:
    """Check if a chat is a registered source channel"""
    channel = await get_source_channel(chat_id)
    return channel is not None


# ============== POSTS ==============

async def add_post(
    source_channel_id: int,
    source_link: str,
    source_chat_id: int,
    source_message_id: int,
    target_chat_id: int,
    target_message_id: int,
    message_text: str = None,
    has_media: bool = False,
    media_type: str = None,
    status: str = 'success'
) -> int:
    """Add a new post record"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO posts
            (source_channel_id, source_link, source_chat_id, source_message_id,
             target_chat_id, target_message_id, message_text, has_media, media_type, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
        ''', source_channel_id, source_link, source_chat_id, source_message_id,
            target_chat_id, target_message_id, message_text, has_media, media_type, status)

        # Update daily stats
        await update_daily_stats(source_channel_id, status == 'success')

        return row['id']


async def get_today_post_count(source_channel_id: int) -> int:
    """Get number of successful posts made today for a source channel"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT COUNT(*) as count FROM posts
            WHERE source_channel_id = $1
            AND DATE(created_at) = CURRENT_DATE
            AND status = 'success'
        ''', source_channel_id)
        return row['count']


async def get_total_post_count(source_channel_id: int = None) -> int:
    """Get total number of successful posts"""
    async with pool.acquire() as conn:
        if source_channel_id:
            row = await conn.fetchrow('''
                SELECT COUNT(*) as count FROM posts
                WHERE source_channel_id = $1 AND status = 'success'
            ''', source_channel_id)
        else:
            row = await conn.fetchrow("SELECT COUNT(*) as count FROM posts WHERE status = 'success'")
        return row['count']


async def get_recent_posts(limit: int = 50, source_channel_id: int = None) -> List[Dict[str, Any]]:
    """Get recent posts"""
    async with pool.acquire() as conn:
        if source_channel_id:
            rows = await conn.fetch('''
                SELECT p.*, sc.source_title, sc.target_title
                FROM posts p
                LEFT JOIN source_channels sc ON p.source_channel_id = sc.id
                WHERE p.source_channel_id = $1
                ORDER BY p.created_at DESC LIMIT $2
            ''', source_channel_id, limit)
        else:
            rows = await conn.fetch('''
                SELECT p.*, sc.source_title, sc.target_title
                FROM posts p
                LEFT JOIN source_channels sc ON p.source_channel_id = sc.id
                ORDER BY p.created_at DESC LIMIT $1
            ''', limit)
        return [dict(row) for row in rows]


async def can_post_today(source_channel_id: int) -> bool:
    """Check if we can still post today for this source channel"""
    async with pool.acquire() as conn:
        # Get channel's daily limit
        channel = await conn.fetchrow(
            'SELECT daily_limit FROM source_channels WHERE id = $1',
            source_channel_id
        )
        if not channel:
            return False

        # Get today's count
        today_count = await get_today_post_count(source_channel_id)
        return today_count < channel['daily_limit']


async def get_remaining_posts_today(source_channel_id: int) -> int:
    """Get remaining posts allowed today"""
    async with pool.acquire() as conn:
        channel = await conn.fetchrow(
            'SELECT daily_limit FROM source_channels WHERE id = $1',
            source_channel_id
        )
        if not channel:
            return 0

        today_count = await get_today_post_count(source_channel_id)
        return max(0, channel['daily_limit'] - today_count)


# ============== STATS ==============

async def update_daily_stats(source_channel_id: int, success: bool):
    """Update daily statistics"""
    async with pool.acquire() as conn:
        today = date.today()

        if success:
            await conn.execute('''
                INSERT INTO daily_stats (source_channel_id, date, post_count, success_count)
                VALUES ($1, $2, 1, 1)
                ON CONFLICT (source_channel_id, date) DO UPDATE
                SET post_count = daily_stats.post_count + 1,
                    success_count = daily_stats.success_count + 1
            ''', source_channel_id, today)
        else:
            await conn.execute('''
                INSERT INTO daily_stats (source_channel_id, date, post_count, failed_count)
                VALUES ($1, $2, 1, 1)
                ON CONFLICT (source_channel_id, date) DO UPDATE
                SET post_count = daily_stats.post_count + 1,
                    failed_count = daily_stats.failed_count + 1
            ''', source_channel_id, today)


async def get_stats_summary() -> Dict[str, Any]:
    """Get overall stats summary"""
    async with pool.acquire() as conn:
        # Today's totals
        today_row = await conn.fetchrow('''
            SELECT
                COALESCE(SUM(post_count), 0) as today_posts,
                COALESCE(SUM(success_count), 0) as today_success,
                COALESCE(SUM(failed_count), 0) as today_failed
            FROM daily_stats WHERE date = CURRENT_DATE
        ''')

        # Total posts
        total_row = await conn.fetchrow('''
            SELECT COUNT(*) as total FROM posts WHERE status = 'success'
        ''')

        # Weekly stats
        weekly_rows = await conn.fetch('''
            SELECT date, SUM(post_count) as posts, SUM(success_count) as success
            FROM daily_stats
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY date ORDER BY date
        ''')

        # Active channels count
        channels_row = await conn.fetchrow('''
            SELECT COUNT(*) as count FROM source_channels WHERE is_active = TRUE
        ''')

        return {
            'today_posts': today_row['today_posts'],
            'today_success': today_row['today_success'],
            'today_failed': today_row['today_failed'],
            'total_posts': total_row['total'],
            'active_channels': channels_row['count'],
            'weekly_stats': [dict(row) for row in weekly_rows]
        }


async def get_channel_stats(source_channel_id: int) -> Dict[str, Any]:
    """Get stats for a specific source channel"""
    async with pool.acquire() as conn:
        today_count = await get_today_post_count(source_channel_id)
        total_count = await get_total_post_count(source_channel_id)

        channel = await conn.fetchrow(
            'SELECT daily_limit FROM source_channels WHERE id = $1',
            source_channel_id
        )

        last_post = await conn.fetchrow('''
            SELECT created_at FROM posts
            WHERE source_channel_id = $1 AND status = 'success'
            ORDER BY created_at DESC LIMIT 1
        ''', source_channel_id)

        return {
            'today_posts': today_count,
            'total_posts': total_count,
            'daily_limit': channel['daily_limit'] if channel else 0,
            'remaining_today': max(0, (channel['daily_limit'] if channel else 0) - today_count),
            'last_post_time': last_post['created_at'].isoformat() if last_post else None
        }
