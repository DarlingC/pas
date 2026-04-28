import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), 'data', 'passwords.db');

let db: Database.Database | null = null;

export function getDb(): Database.Database {
  if (!db) {
    const fs = require('fs');
    const dir = path.dirname(DB_PATH);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    db = new Database(DB_PATH);
    initSchema();
  }
  return db;
}

function initSchema(): void {
  const database = db!;
  database.exec(`
    CREATE TABLE IF NOT EXISTS passwords (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT NOT NULL UNIQUE,
      user_name TEXT,
      password TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);
}

export interface PasswordRecord {
  id: number;
  user_id: string;
  user_name: string | null;
  password: string;
  created_at: string;
  updated_at: string;
}

export function savePassword(userId: string, userName: string | null, password: string): boolean {
  const database = getDb();
  const stmt = database.prepare(`
    INSERT INTO passwords (user_id, user_name, password, updated_at)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(user_id) DO UPDATE SET
      password = excluded.password,
      user_name = COALESCE(excluded.user_name, user_name),
      updated_at = CURRENT_TIMESTAMP
  `);
  const result = stmt.run(userId, userName, password);
  return result.changes > 0;
}

export function getPasswordByUserId(userId: string): PasswordRecord | null {
  const database = getDb();
  const stmt = database.prepare('SELECT * FROM passwords WHERE user_id = ?');
  const result = stmt.get(userId) as PasswordRecord | undefined;
  return result || null;
}

export function closeDb(): void {
  if (db) {
    db.close();
    db = null;
  }
}
