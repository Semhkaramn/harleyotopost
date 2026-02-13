import { Pool, types } from 'pg';

// BigInt'leri string olarak döndür (JavaScript number sınırları için)
types.setTypeParser(20, (val) => val);

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false
  },
  // Timeout ayarları
  statement_timeout: 30000,
  query_timeout: 30000,
});

export default pool;

export async function query(text: string, params?: unknown[]) {
  const client = await pool.connect();
  try {
    // name: undefined ile prepared statement önbelleğini atla (Heroku PgBouncer uyumluluğu)
    const result = await client.query({
      text,
      values: params,
      name: undefined  // Prepared statement kullanma
    });
    return result;
  } finally {
    client.release();
  }
}
