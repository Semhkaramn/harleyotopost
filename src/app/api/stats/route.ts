import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function GET() {
  try {
    // Today's totals
    const todayResult = await query(`
      SELECT
        COALESCE(SUM(post_count), 0) as today_posts,
        COALESCE(SUM(success_count), 0) as today_success,
        COALESCE(SUM(failed_count), 0) as today_failed
      FROM daily_stats WHERE date = CURRENT_DATE
    `);

    // Total posts
    const totalResult = await query(`
      SELECT COUNT(*) as total FROM posts WHERE status = 'success'
    `);

    // Weekly stats
    const weeklyResult = await query(`
      SELECT
        date,
        COALESCE(SUM(post_count), 0) as posts,
        COALESCE(SUM(success_count), 0) as success
      FROM daily_stats
      WHERE date >= CURRENT_DATE - INTERVAL '7 days'
      GROUP BY date
      ORDER BY date
    `);

    // Active channels count
    const channelsResult = await query(`
      SELECT COUNT(*) as count FROM source_channels WHERE is_active = TRUE
    `);

    // Bot status
    const botStatusResult = await query(`
      SELECT value FROM settings WHERE key = 'bot_status'
    `);

    // Bot enabled
    const botEnabledResult = await query(`
      SELECT value FROM settings WHERE key = 'bot_enabled'
    `);

    // Last post time
    const lastPostResult = await query(`
      SELECT created_at FROM posts
      WHERE status = 'success'
      ORDER BY created_at DESC LIMIT 1
    `);

    const todayRow = todayResult.rows[0];

    return NextResponse.json({
      today_posts: parseInt(todayRow?.today_posts || '0'),
      today_success: parseInt(todayRow?.today_success || '0'),
      today_failed: parseInt(todayRow?.today_failed || '0'),
      total_posts: parseInt(totalResult.rows[0]?.total || '0'),
      active_channels: parseInt(channelsResult.rows[0]?.count || '0'),
      weekly_stats: weeklyResult.rows,
      bot_status: botStatusResult.rows[0]?.value || 'offline',
      bot_enabled: botEnabledResult.rows[0]?.value === 'true',
      last_post_time: lastPostResult.rows[0]?.created_at || null
    });
  } catch (error) {
    console.error('Error fetching stats:', error);
    return NextResponse.json({ error: 'Failed to fetch stats' }, { status: 500 });
  }
}
