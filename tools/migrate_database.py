#!/usr/bin/env python3
"""
Database Migration Script

Migrates data from old SQLite databases to new unified database structure.
Supports migrating to either SQLite or PostgreSQL based on DATABASE_URL.

Usage:
    # Migrate to SQLite (development)
    python tools/migrate_database.py
    
    # Migrate to PostgreSQL (production)
    DATABASE_URL=postgresql://user:pass@host/db python tools/migrate_database.py
    
    # Dry run (show what would be migrated)
    python tools/migrate_database.py --dry-run
"""

import os
import sys
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_manager, run_migration
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Migrate BabbleBeaver databases to new unified schema'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without making changes'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force migration even if tables already exist'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("BabbleBeaver Database Migration Tool")
    print("=" * 70)
    print()
    
    # Show current database configuration
    print(f"Target Database: {db_manager.db_type.upper()}")
    if db_manager.db_type == 'postgresql':
        # Hide password in URL
        url = db_manager.database_url
        if '@' in url:
            parts = url.split('@')
            user_pass = parts[0].split('://')[1]
            host_db = parts[1]
            safe_url = f"postgresql://{'*' * len(user_pass)}@{host_db}"
        else:
            safe_url = url
        print(f"Database URL: {safe_url}")
    else:
        print(f"Database Path: db/babblebeaver.db")
    print()
    
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made")
        print()
    
    # Check for old databases
    old_dbs = []
    if os.path.exists('chatbot.db'):
        old_dbs.append('chatbot.db')
    if os.path.exists('db/tokens.db'):
        old_dbs.append('db/tokens.db')
    
    if not old_dbs:
        print("✓ No old databases found. Nothing to migrate.")
        print()
        print("New database structure is ready to use!")
        return
    
    print(f"Found {len(old_dbs)} old database(s) to migrate:")
    for db in old_dbs:
        print(f"  - {db}")
    print()
    
    if args.dry_run:
        print("Would perform migration steps:")
        print("  1. Create new unified database schema")
        print("  2. Copy all messages from chatbot.db")
        print("  3. Copy all API tokens from db/tokens.db")
        print("  4. Verify data integrity")
        print()
        print("Run without --dry-run to perform actual migration")
        return
    
    # Confirm migration
    if not args.force:
        response = input("Proceed with migration? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Migration cancelled.")
            return
    
    print()
    print("Starting migration...")
    print()
    
    try:
        # Run the migration
        run_migration()
        
        print()
        print("=" * 70)
        print("✓ Migration completed successfully!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Test the application to ensure everything works")
        print("  2. Backup old database files:")
        print("     mkdir -p backups")
        print("     mv chatbot.db backups/chatbot.db.backup")
        print("     mv db/tokens.db backups/tokens.db.backup")
        print("  3. Update your code to use new imports:")
        print("     from message_logger_new import message_logger")
        print("     from token_manager_new import token_manager")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("✗ Migration failed!")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        print("Your original databases are unchanged.")
        sys.exit(1)


if __name__ == '__main__':
    main()
