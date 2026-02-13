import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function GET() {
  try {
    // First ensure the table exists
    await query(`
      CREATE TABLE IF NOT EXISTS target_channels (
        id SERIAL PRIMARY KEY,
        chat_id VARCHAR(255) UNIQUE NOT NULL,
        title VARCHAR(255) NOT NULL,
        username VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    const result = await query(`
      SELECT * FROM target_channels
      WHERE is_active = TRUE
      ORDER BY created_at DESC
    `);

    return NextResponse.json(result.rows);
  } catch (error) {
    console.error('Error fetching target channels:', error);
    return NextResponse.json({ error: 'Failed to fetch target channels' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { chat_id, title, username } = body;

    if (!chat_id || !title) {
      return NextResponse.json({ error: 'chat_id and title are required' }, { status: 400 });
    }

    // Ensure table exists
    await query(`
      CREATE TABLE IF NOT EXISTS target_channels (
        id SERIAL PRIMARY KEY,
        chat_id VARCHAR(255) UNIQUE NOT NULL,
        title VARCHAR(255) NOT NULL,
        username VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    const result = await query(
      `INSERT INTO target_channels (chat_id, title, username)
       VALUES ($1, $2, $3)
       ON CONFLICT (chat_id) DO UPDATE SET
         title = $2,
         username = COALESCE($3, target_channels.username),
         updated_at = CURRENT_TIMESTAMP
       RETURNING *`,
      [chat_id, title, username || null]
    );

    return NextResponse.json(result.rows[0]);
  } catch (error) {
    console.error('Error creating target channel:', error);
    return NextResponse.json({ error: 'Failed to create target channel' }, { status: 500 });
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json();
    const { id, title, username, is_active } = body;

    const setClause: string[] = [];
    const values: unknown[] = [id];
    let paramIndex = 2;

    if (title !== undefined) {
      setClause.push(`title = $${paramIndex}`);
      values.push(title);
      paramIndex++;
    }
    if (username !== undefined) {
      setClause.push(`username = $${paramIndex}`);
      values.push(username);
      paramIndex++;
    }
    if (is_active !== undefined) {
      setClause.push(`is_active = $${paramIndex}`);
      values.push(is_active);
      paramIndex++;
    }

    if (setClause.length === 0) {
      return NextResponse.json({ error: 'No fields to update' }, { status: 400 });
    }

    setClause.push('updated_at = CURRENT_TIMESTAMP');

    const result = await query(
      `UPDATE target_channels SET ${setClause.join(', ')} WHERE id = $1 RETURNING *`,
      values
    );

    return NextResponse.json(result.rows[0]);
  } catch (error) {
    console.error('Error updating target channel:', error);
    return NextResponse.json({ error: 'Failed to update target channel' }, { status: 500 });
  }
}

export async function DELETE(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json({ error: 'Missing channel ID' }, { status: 400 });
    }

    // Check if this target channel is used by any source channels
    const usageCheck = await query(
      'SELECT COUNT(*) as count FROM source_channels WHERE target_channel_id = $1',
      [id]
    );

    if (parseInt(usageCheck.rows[0]?.count || '0') > 0) {
      return NextResponse.json(
        { error: 'Bu hedef kanal kullanımda. Önce dinleme kanallarından kaldırın.' },
        { status: 400 }
      );
    }

    await query('DELETE FROM target_channels WHERE id = $1', [id]);

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting target channel:', error);
    return NextResponse.json({ error: 'Failed to delete target channel' }, { status: 500 });
  }
}
