"""
Database Models and Configuration

Centralized database models using SQLAlchemy ORM.
Supports SQLite for development and PostgreSQL for production.
"""

import os
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()


class Message(Base):
    """Chat message log model."""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text)
    provider = Column(String(50), index=True)
    model = Column(String(100))
    tokens_used = Column(Integer)
    metadata_ = Column('metadata', JSON)  # Rename to avoid SQLAlchemy reserved word
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_message': self.user_message,
            'bot_response': self.bot_response,
            'provider': self.provider,
            'model': self.model,
            'tokens_used': self.tokens_used,
            'metadata': self.metadata_
        }


class APIToken(Base):
    """API token model."""
    __tablename__ = 'api_tokens'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert model to dictionary."""
        now = datetime.utcnow()
        is_expired = self.expires_at and self.expires_at < now
        
        return {
            'id': self.id,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_expired': is_expired,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None
        }


class DatabaseManager:
    """
    Database manager with automatic SQLite/PostgreSQL switching.
    
    Environment Variables:
        DATABASE_URL: PostgreSQL connection string (e.g., postgresql://user:pass@host/db)
        If not set, uses SQLite with local db/babblebeaver.db file
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            database_url: Override database URL (optional)
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        
        # Determine database type and configure connection
        if self.database_url and self.database_url.startswith('postgresql://'):
            self.db_type = 'postgresql'
            self.engine = create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Verify connections before using
                echo=False
            )
            logger.info("Using PostgreSQL database")
        else:
            self.db_type = 'sqlite'
            # Create db directory if it doesn't exist
            db_dir = 'db'
            os.makedirs(db_dir, exist_ok=True)
            sqlite_path = f'{db_dir}/babblebeaver.db'
            self.database_url = f'sqlite:///{sqlite_path}'
            self.engine = create_engine(
                self.database_url,
                connect_args={'check_same_thread': False},  # SQLite specific
                echo=False
            )
            logger.info(f"Using SQLite database: {sqlite_path}")
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Create tables
        self._create_tables()
    
    def _create_tables(self):
        """Create all tables if they don't exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions.
        
        Usage:
            with db_manager.get_session() as session:
                user = session.query(User).first()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def migrate_from_old_sqlite(self, old_db_path: str = 'chatbot.db'):
        """
        Migrate data from old SQLite database to new schema.
        
        Args:
            old_db_path: Path to old chatbot.db file
        """
        if not os.path.exists(old_db_path):
            logger.info(f"Old database {old_db_path} not found. No migration needed.")
            return
        
        import sqlite3
        
        logger.info(f"Migrating data from {old_db_path}...")
        
        # Connect to old database
        old_conn = sqlite3.connect(old_db_path)
        old_conn.row_factory = sqlite3.Row
        old_cursor = old_conn.cursor()
        
        try:
            # Migrate messages
            old_cursor.execute("SELECT * FROM messages ORDER BY id")
            messages = old_cursor.fetchall()
            
            with self.get_session() as session:
                migrated_count = 0
                for row in messages:
                    # Check if message already exists
                    existing = session.query(Message).filter_by(id=row['id']).first()
                    if existing:
                        continue
                    
                    # Parse metadata if it's a JSON string
                    metadata = row['metadata']
                    if isinstance(metadata, str):
                        import json
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}
                    
                    message = Message(
                        id=row['id'],
                        timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
                        user_message=row['user_message'],
                        bot_response=row['bot_response'],
                        provider=row['provider'],
                        model=row['model'],
                        tokens_used=row['tokens_used'],
                        metadata=metadata
                    )
                    session.add(message)
                    migrated_count += 1
                
                logger.info(f"Migrated {migrated_count} messages")
            
            # Migrate tokens (if old tokens table exists)
            try:
                old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tokens'")
                if old_cursor.fetchone():
                    old_cursor.execute("SELECT * FROM tokens")
                    tokens = old_cursor.fetchall()
                    
                    with self.get_session() as session:
                        token_count = 0
                        for row in tokens:
                            existing = session.query(APIToken).filter_by(id=row['id']).first()
                            if existing:
                                continue
                            
                            token = APIToken(
                                id=row['id'],
                                token_hash=row['token_hash'],
                                description=row['description'],
                                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                                expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                                is_active=bool(row['is_active']),
                                last_used_at=datetime.fromisoformat(row['last_used_at']) if row['last_used_at'] else None
                            )
                            session.add(token)
                            token_count += 1
                        
                        logger.info(f"Migrated {token_count} API tokens")
            except sqlite3.Error:
                logger.info("No tokens table in old database")
            
        except Exception as e:
            logger.error(f"Migration error: {e}")
            raise
        finally:
            old_conn.close()
        
        logger.info("Migration completed successfully")


# Global database manager instance
db_manager = DatabaseManager()


def get_db_session():
    """
    Dependency for FastAPI endpoints to get database session.
    
    Usage in FastAPI:
        @app.get("/messages")
        def get_messages(db: Session = Depends(get_db_session)):
            messages = db.query(Message).all()
            return messages
    """
    with db_manager.get_session() as session:
        yield session


# Convenience function for migrations
def run_migration():
    """Run database migration from old SQLite database."""
    db_manager.migrate_from_old_sqlite('chatbot.db')
    db_manager.migrate_from_old_sqlite('db/tokens.db')
