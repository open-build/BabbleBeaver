"""
Database migration script for BabbleBeaver message logger.
Upgrades the old messages table schema to the new enhanced schema.

Run this script once to migrate your existing database:
    python migrate_db.py
"""

import sqlite3
import os
from datetime import datetime


def migrate_database(db_path="chatbot.db"):
    """
    Migrate the messages table from old schema to new schema.
    
    Old schema:
        id INTEGER PRIMARY KEY,
        message TEXT NOT NULL
    
    New schema:
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_message TEXT NOT NULL,
        bot_response TEXT,
        provider TEXT,
        model TEXT,
        tokens_used INTEGER,
        metadata TEXT
    """
    
    print(f"Starting migration for database: {db_path}")
    
    if not os.path.exists(db_path):
        print("Database does not exist. No migration needed.")
        print("The new schema will be created automatically on first run.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if the old schema exists
        cursor.execute("PRAGMA table_info(messages)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"Current columns: {columns}")
        
        # If we already have the new schema, no migration needed
        if 'user_message' in columns and 'bot_response' in columns:
            print("Database already has new schema. No migration needed.")
            conn.close()
            return
        
        # If we have the old schema with just 'message' column
        if 'message' in columns and 'user_message' not in columns:
            print("Old schema detected. Starting migration...")
            
            # Create backup table
            print("Creating backup table...")
            cursor.execute("""
                CREATE TABLE messages_backup AS 
                SELECT * FROM messages
            """)
            
            # Drop old table
            print("Dropping old messages table...")
            cursor.execute("DROP TABLE messages")
            
            # Create new table with enhanced schema
            print("Creating new messages table with enhanced schema...")
            cursor.execute("""
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_message TEXT NOT NULL,
                    bot_response TEXT,
                    provider TEXT,
                    model TEXT,
                    tokens_used INTEGER,
                    metadata TEXT
                )
            """)
            
            # Migrate data from backup
            print("Migrating data from backup...")
            cursor.execute("""
                INSERT INTO messages (id, timestamp, user_message)
                SELECT id, CURRENT_TIMESTAMP, message
                FROM messages_backup
            """)
            
            # Create indexes
            print("Creating indexes...")
            cursor.execute("""
                CREATE INDEX idx_timestamp ON messages(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX idx_provider ON messages(provider)
            """)
            
            # Get migration stats
            cursor.execute("SELECT COUNT(*) FROM messages")
            migrated_count = cursor.fetchone()[0]
            
            conn.commit()
            print(f"Migration successful! {migrated_count} messages migrated.")
            
            # Drop backup table
            print("Cleaning up backup table...")
            cursor.execute("DROP TABLE messages_backup")
            conn.commit()
            
            print("Migration complete!")
            
        else:
            print("Unknown schema detected. Manual intervention required.")
            print(f"Columns found: {columns}")
    
    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        print("Migration rolled back. Database is unchanged.")
    
    finally:
        conn.close()


if __name__ == "__main__":
    print("BabbleBeaver Database Migration Tool")
    print("=" * 50)
    
    # Check if custom db path is provided
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "chatbot.db"
    
    migrate_database(db_path)
    
    print("\nMigration process finished.")
    print("\nNext steps:")
    print("1. Review your .env file and add admin credentials")
    print("2. Install new requirements: pip install -r requirements.txt")
    print("3. Start the application: uvicorn main:app --reload")
    print("4. Access admin dashboard: http://localhost:8000/admin/login-page")
