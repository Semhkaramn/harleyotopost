import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function GET() {
  try {
    const result = await query(`
      SELECT
        sc.*,
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
    const body = await request.json();
    const {
      source_chat_id,
      target_chat_id,
      source_title,
      source_username,
      target_title,
      append_link,
      daily_limit,
      remove_links,
      remove_emojis
    } = body;

    const result = await query(
      `INSERT INTO source_channels
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
       RETURNING *`,
      [
        source_chat_id,
        target_chat_id,
        source_title || null,
        source_username || null,
        target_title || null,
        append_link || '',
        daily_limit || 4,
        remove_links !== false,
        remove_emojis === true
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
    const body = await request.json();
    const { id, ...updates } = body;

    const setClause: string[] = [];
    const values: unknown[] = [id];
    let paramIndex = 2;

    const allowedFields = [
      'target_chat_id', 'source_title', 'target_title',
      'append_link', 'daily_limit', 'remove_links', 'remove_emojis', 'is_active'
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
