import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

// Ensure table structure is updated
async function ensureTableStructure() {
  try {
    // Add target_channel_id column if it doesn't exist
    await query(`
      ALTER TABLE source_channels
      ADD COLUMN IF NOT EXISTS target_channel_id INTEGER
    `);
    // Add append_link_text column if it doesn't exist
    await query(`
      ALTER TABLE source_channels
      ADD COLUMN IF NOT EXISTS append_link_text TEXT DEFAULT ''
    `);
  } catch {
    // Column might already exist, ignore error
  }
}

export async function GET() {
  try {
    await ensureTableStructure();

    const result = await query(`
      SELECT
        sc.*,
        tc.title as target_channel_title,
        tc.chat_id as target_channel_chat_id,
        COALESCE(
          (SELECT COUNT(*) FROM posts p
           WHERE p.source_channel_id = sc.id
           AND DATE(p.created_at) = CURRENT_DATE
           AND p.status = 'success'), 0
        ) as today_posts,
        COALESCE(
          (SELECT COUNT(*) FROM posts p
           WHERE p.source_channel_id = sc.id
           AND p.status = 'success'), 0
        ) as total_posts
      FROM source_channels sc
      LEFT JOIN target_channels tc ON sc.target_channel_id = tc.id
      ORDER BY sc.created_at DESC
    `);

    return NextResponse.json(result.rows);
  } catch (error) {
    console.error('Error fetching channels:', error);
    return NextResponse.json({ error: 'Failed to fetch channels' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    await ensureTableStructure();

    const body = await request.json();
    const {
      source_chat_id,
      target_channel_id,
      target_chat_id,
      source_title,
      source_username,
      target_title,
      append_link,
      append_link_text,
      daily_limit,
      remove_links,
      listen_type,
      trigger_keywords,
      send_link_back
    } = body;

    // If target_channel_id is provided, get the target chat_id from target_channels
    let finalTargetChatId = target_chat_id;
    let finalTargetTitle = target_title;

    if (target_channel_id) {
      const targetChannel = await query(
        'SELECT chat_id, title FROM target_channels WHERE id = $1',
        [target_channel_id]
      );
      if (targetChannel.rows[0]) {
        finalTargetChatId = targetChannel.rows[0].chat_id;
        finalTargetTitle = targetChannel.rows[0].title;
      }
    }

    // source_chat_id ve target_chat_id'yi BigInt olarak parse et
    const parsedSourceChatId = BigInt(String(source_chat_id).replace(/[^0-9-]/g, ''));
    const parsedTargetChatId = finalTargetChatId ? BigInt(String(finalTargetChatId).replace(/[^0-9-]/g, '')) : null;

    const result = await query(
      `INSERT INTO source_channels
       (source_chat_id, target_chat_id, target_channel_id, source_title, source_username,
        target_title, append_link, append_link_text, daily_limit, remove_links,
        listen_type, trigger_keywords, send_link_back)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
       ON CONFLICT (source_chat_id) DO UPDATE SET
         target_chat_id = $2,
         target_channel_id = $3,
         source_title = COALESCE($4, source_channels.source_title),
         source_username = COALESCE($5, source_channels.source_username),
         target_title = COALESCE($6, source_channels.target_title),
         append_link = $7,
         append_link_text = $8,
         daily_limit = $9,
         remove_links = $10,
         listen_type = $11,
         trigger_keywords = $12,
         send_link_back = $13,
         updated_at = CURRENT_TIMESTAMP
       RETURNING *`,
      [
        parsedSourceChatId.toString(),
        parsedTargetChatId?.toString() || null,
        target_channel_id || null,
        source_title || null,
        source_username || null,
        finalTargetTitle || null,
        append_link || '',
        append_link_text || '',
        daily_limit || 4,
        remove_links !== false,
        listen_type || 'direct',
        trigger_keywords || '',
        send_link_back === true
      ]
    );

    return NextResponse.json(result.rows[0]);
  } catch (error) {
    console.error('Error creating channel:', error);
    return NextResponse.json({ error: 'Failed to create channel' }, { status: 500 });
  }
}

export async function PUT(request: Request) {
  try {
    await ensureTableStructure();

    const body = await request.json();
    const { id, target_channel_id, ...updates } = body;

    // ID doğrulaması
    if (!id) {
      return NextResponse.json({ error: 'Channel ID is required' }, { status: 400 });
    }

    const setClause: string[] = [];
    // ID'yi integer olarak dönüştür
    const values: unknown[] = [parseInt(String(id))];
    let paramIndex = 2;

    // If target_channel_id is being updated, also update target_chat_id and target_title
    if (target_channel_id !== undefined) {
      if (target_channel_id) {
        const targetChannel = await query(
          'SELECT chat_id, title FROM target_channels WHERE id = $1',
          [target_channel_id]
        );
        if (targetChannel.rows[0]) {
          setClause.push(`target_channel_id = $${paramIndex}`);
          values.push(target_channel_id);
          paramIndex++;

          setClause.push(`target_chat_id = $${paramIndex}`);
          values.push(targetChannel.rows[0].chat_id);
          paramIndex++;

          setClause.push(`target_title = $${paramIndex}`);
          values.push(targetChannel.rows[0].title);
          paramIndex++;
        }
      } else {
        setClause.push(`target_channel_id = $${paramIndex}`);
        values.push(null);
        paramIndex++;
      }
    }

    // source_chat_id is UNIQUE and should not be changed after creation
    const allowedFields = [
      'source_title', 'source_username',
      'target_chat_id', 'target_title',
      'append_link', 'append_link_text', 'daily_limit', 'remove_links', 'is_active',
      'listen_type', 'trigger_keywords', 'send_link_back'
    ];

    for (const field of allowedFields) {
      if (updates[field] !== undefined) {
        setClause.push(`${field} = $${paramIndex}`);
        values.push(updates[field]);
        paramIndex++;
      }
    }

    if (setClause.length === 0) {
      return NextResponse.json({ error: 'No fields to update' }, { status: 400 });
    }

    setClause.push('updated_at = CURRENT_TIMESTAMP');

    const result = await query(
      `UPDATE source_channels SET ${setClause.join(', ')} WHERE id = $1 RETURNING *`,
      values
    );

    return NextResponse.json(result.rows[0]);
  } catch (error) {
    console.error('Error updating channel:', error);
    return NextResponse.json({ error: 'Failed to update channel' }, { status: 500 });
  }
}

export async function DELETE(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json({ error: 'Missing channel ID' }, { status: 400 });
    }

    await query('DELETE FROM source_channels WHERE id = $1', [id]);

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting channel:', error);
    return NextResponse.json({ error: 'Failed to delete channel' }, { status: 500 });
  }
}
