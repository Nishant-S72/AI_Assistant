import { Pool } from 'pg';
import * as fs from 'fs';
import * as path from 'path';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || 'postgres://postgres:postgres@localhost:5432/aichief',
});

// Initialize database schema
/**
 * Run database migrations
 */
async function runMigrations() {
  try {
    const migrationsPath = path.join(__dirname, '../db/migrations');
    if (!fs.existsSync(migrationsPath)) {
      console.log('No migrations directory found, skipping migrations');
      return;
    }

    const migrationFiles = fs
      .readdirSync(migrationsPath)
      .filter((f) => f.endsWith('.sql'))
      .sort();

    for (const file of migrationFiles) {
      const filePath = path.join(migrationsPath, file);
      const sql = fs.readFileSync(filePath, 'utf-8');
      
      try {
        await pool.query(sql);
        console.log(`✅ Applied migration: ${file}`);
      } catch (error: any) {
        // Ignore "already exists" errors
        if (error.message?.includes('already exists') || error.code === '42710') {
          console.log(`⏭️  Migration already applied: ${file}`);
        } else {
          console.warn(`⚠️  Migration ${file} failed:`, error.message);
        }
      }
    }
  } catch (error: any) {
    console.warn('Could not run migrations:', error.message);
  }
}

export async function initDatabase() {
  try {
    // Try multiple paths to find schema.sql
    const possiblePaths = [
      path.join(__dirname, 'schema.sql'), // dist/db/schema.sql (production)
      path.join(__dirname, '../src/db/schema.sql'), // src/db/schema.sql (from dist)
      path.join(process.cwd(), 'backend/src/db/schema.sql'), // absolute from project root
      path.join(process.cwd(), 'src/db/schema.sql'), // if running from backend dir
    ];
    
    let schemaPath: string | null = null;
    for (const possiblePath of possiblePaths) {
      if (fs.existsSync(possiblePath)) {
        schemaPath = possiblePath;
        break;
      }
    }
    
    if (!schemaPath) {
      console.warn('⚠️  Schema file not found, skipping initialization');
      console.warn('   Tried paths:', possiblePaths);
      return;
    }
    
    const schema = fs.readFileSync(schemaPath, 'utf-8');
    await pool.query(schema);
    console.log('✅ Database schema initialized from:', schemaPath);
    
    // Run migrations after schema initialization
    await runMigrations();
  } catch (error: any) {
    // If it's a "relation already exists" error, that's okay
    if (error.message && error.message.includes('already exists')) {
      console.log('✅ Database schema already exists');
      // Still run migrations even if tables exist
      await runMigrations();
      return;
    }
    console.error('❌ Error initializing database:', error.message || error);
    // Don't throw - allow server to start even if schema init fails
  }
}

export { pool };

