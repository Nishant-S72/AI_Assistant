"""
Migration script to add thread_id and message_id columns to tasks table.
This links tasks to their corresponding conversations.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def add_task_columns():
    """Add thread_id and message_id columns to tasks table if they don't exist."""
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    try:
        # Check if columns exist
        columns = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tasks' 
            AND column_name IN ('thread_id', 'message_id')
        """)
        existing_columns = {row['column_name'] for row in columns}
        
        # Add thread_id if it doesn't exist
        if 'thread_id' not in existing_columns:
            print("Adding thread_id column to tasks table...")
            await conn.execute("""
                ALTER TABLE tasks 
                ADD COLUMN thread_id TEXT
            """)
            print("✅ Added thread_id column")
        else:
            print("✅ thread_id column already exists")
        
        # Add message_id if it doesn't exist
        if 'message_id' not in existing_columns:
            print("Adding message_id column to tasks table...")
            await conn.execute("""
                ALTER TABLE tasks 
                ADD COLUMN message_id TEXT
            """)
            print("✅ Added message_id column")
        else:
            print("✅ message_id column already exists")
        
        # Add indexes for better query performance
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_thread_id ON tasks(thread_id)
            """)
            print("✅ Created index on thread_id")
        except Exception as e:
            print(f"Note: Index on thread_id may already exist: {e}")
        
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_message_id ON tasks(message_id)
            """)
            print("✅ Created index on message_id")
        except Exception as e:
            print(f"Note: Index on message_id may already exist: {e}")
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(add_task_columns())

