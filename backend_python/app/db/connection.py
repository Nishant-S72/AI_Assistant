"""Database connection and initialization."""
import os
import asyncio
from pathlib import Path
from typing import Optional
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# Global connection pool
pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create database connection pool."""
    global pool
    if pool is None:
        database_url = os.getenv(
            "DATABASE_URL", "postgres://postgres:postgres@localhost:5432/aichief"
        )
        pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
    return pool


async def run_migrations() -> None:
    """Run database migrations."""
    try:
        migrations_path = Path(__file__).parent.parent.parent / "db" / "migrations"
        if not migrations_path.exists():
            print("No migrations directory found, skipping migrations")
            return

        migration_files = sorted(
            [f for f in migrations_path.iterdir() if f.suffix == ".sql"]
        )

        db_pool = await get_pool()
        for file in migration_files:
            sql = file.read_text(encoding="utf-8")
            try:
                async with db_pool.acquire() as conn:
                    await conn.execute(sql)
                print(f"✅ Applied migration: {file.name}")
            except Exception as error:
                error_msg = str(error)
                # Ignore "already exists" errors
                if "already exists" in error_msg or "42710" in error_msg:
                    print(f"⏭️  Migration already applied: {file.name}")
                else:
                    print(f"⚠️  Migration {file.name} failed: {error_msg}")
    except Exception as error:
        print(f"Could not run migrations: {error}")


async def init_database() -> None:
    """Initialize database schema and run migrations."""
    try:
        # Try multiple paths to find schema.sql
        possible_paths = [
            Path(__file__).parent / "schema.sql",  # app/db/schema.sql
            Path(__file__).parent.parent.parent / "db" / "schema.sql",  # backend/db/schema.sql
            Path(__file__).parent.parent.parent.parent / "backend" / "src" / "db" / "schema.sql",  # from project root
        ]

        schema_path: Optional[Path] = None
        for possible_path in possible_paths:
            if possible_path.exists():
                schema_path = possible_path
                break

        if not schema_path:
            print("⚠️  Schema file not found, skipping initialization")
            print(f"   Tried paths: {[str(p) for p in possible_paths]}")
            return

        schema = schema_path.read_text(encoding="utf-8")
        db_pool = await get_pool()
        async with db_pool.acquire() as conn:
            await conn.execute(schema)
        print(f"✅ Database schema initialized from: {schema_path}")

        # Run migrations after schema initialization
        await run_migrations()
    except Exception as error:
        error_msg = str(error)
        # If it's a "relation already exists" error, that's okay
        if "already exists" in error_msg:
            print("✅ Database schema already exists")
            # Still run migrations even if tables exist
            await run_migrations()
            return
        print(f"❌ Error initializing database: {error_msg}")
        # Don't raise - allow server to start even if schema init fails


async def close_pool() -> None:
    """Close database connection pool."""
    global pool
    if pool:
        await pool.close()
        pool = None

