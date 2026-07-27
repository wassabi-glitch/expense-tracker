/**
 * Helper: extract verification/reset tokens from PostgreSQL (Docker).
 * Usage: node db-token.mjs <email> [verification|reset]
 */
import pkg from 'pg';
const { Client } = pkg;

const email = process.argv[2];
const type = process.argv[3] || 'verification';

if (!email) {
  console.error('Usage: node db-token.mjs <email> [verification|reset]');
  process.exit(1);
}

const client = new Client({
  host: 'localhost',
  port: 5433,
  database: 'ExpenseTracker',
  user: 'postgres',
  password: 'helloPostgres',
});

try {
  await client.connect();
  const table = type === 'reset' ? 'password_reset_tokens' : 'email_verification_tokens';
  const res = await client.query(`
    SELECT token FROM ${table}
    JOIN users ON users.id = ${table}.user_id
    WHERE users.email = $1
    ORDER BY ${table}.created_at DESC
    LIMIT 1
  `, [email]);
  await client.end();

  if (res.rows.length > 0) {
    console.log(res.rows[0].token);
  } else {
    console.error(`No ${type} token found for ${email}`);
    process.exit(1);
  }
} catch (err) {
  console.error('DB error:', err.message);
  process.exit(1);
}
