import { Pool, types } from 'pg';

// BigInt'leri string olarak döndür (JavaScript number sınırları için)
types.setTypeParser(20, (val) => val);

// Heroku/Neon PgBouncer uyumluluğu için pool ayarları
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false
  },
  // Bağlantı ayarları
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
});

export default pool;

export async function query(text: string, params?: unknown[]) {
  // Doğrudan pool.query kullan - prepared statement kullanmaz
  // Bu Heroku PgBouncer ve Neon ile uyumlu
  try {
    const result = await pool.query(text, params);
    return result;
  } catch (error) {
    console.error('Database query error:', error);
    throw error;
  }
}
