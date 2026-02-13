import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '50');
    const channelId = searchParams.get('channel_id');

    let sql = `
      SELECT
        p.*,
        sc.source_title,
        sc.target_title
      FROM posts p
      LEFT JOIN source_channels sc ON p.source_channel_id = sc.id
    `;

    const values: unknown[] = [];

    if (channelId) {
      sql += ' WHERE p.source_channel_id = $1';
      values.push(channelId);
      sql += ' ORDER BY p.created_at DESC LIMIT $2';
      values.push(limit);
    } else {
      sql += ' ORDER BY p.created_at DESC LIMIT $1';
      values.push(limit);
    }

    const result = await query(sql, values);

    return NextResponse.json(result.rows);
  } catch (error) {
    console.error('Error fetching posts:', error);
    return NextResponse.json({ error: 'Failed to fetch posts' }, { status: 500 });
  }
}
