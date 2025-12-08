import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    psycopg2 = None
    RealDictCursor = None

logger = logging.getLogger(__name__)

"""
Log messages sent through the chatbot and allow for retrieving them later.
Supports both SQLite (local development) and PostgreSQL (production).
Database type is determined by DATABASE_URL environment variable.
"""


class MessageLogger:
    def __init__(self, db_path="chatbot.db"):
        self.db_url = os.getenv("DATABASE_URL")
        self.db_path = db_path
        
        # Determine database type
        if self.db_url and self.db_url.startswith("postgresql://"):
            if not POSTGRES_AVAILABLE:
                raise RuntimeError("PostgreSQL database URL provided but psycopg2 not installed")
            self.db_type = "postgresql"
            logger.info(f"Using PostgreSQL database")
        else:
            self.db_type = "sqlite"
            logger.info(f"Using SQLite database: {db_path}")
        
        self._create_table()

    def _create_table(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Enhanced messages table with timestamp, response, and metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
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
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON messages(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_provider 
                ON messages(provider)
            """)

    def log_message(
        self, 
        message: str, 
        response: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Log a message with optional response and metadata.
        
        Args:
            message: User's message
            response: Bot's response
            provider: LLM provider used (e.g., 'gemini', 'openai')
            model: Model name used
            tokens_used: Number of tokens used
            metadata: Additional metadata as dictionary
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute("""
                INSERT INTO messages 
                (user_message, bot_response, provider, model, tokens_used, metadata) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message, response, provider, model, tokens_used, metadata_json))
            
            conn.commit()
            return cursor.lastrowid

    def retrieve_messages(
        self, 
        limit: Optional[int] = None,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve messages with optional filtering.
        
        Args:
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            start_date: Filter messages after this date (ISO format)
            end_date: Filter messages before this date (ISO format)
            provider: Filter by LLM provider
            
        Returns:
            List of message dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM messages WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            if provider:
                query += " AND provider = ?"
                params.append(provider)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                message = dict(row)
                # Parse metadata JSON
                if message.get('metadata'):
                    try:
                        message['metadata'] = json.loads(message['metadata'])
                    except json.JSONDecodeError:
                        message['metadata'] = None
                messages.append(message)
            
            return messages

    def get_message_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: Optional[str] = None
    ) -> int:
        """Get count of messages with optional filtering."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = "SELECT COUNT(*) FROM messages WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            if provider:
                query += " AND provider = ?"
                params.append(provider)
            
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def export_for_fine_tuning(
        self,
        format: str = "jsonl",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        provider: Optional[str] = None
    ) -> str:
        """
        Export messages in format suitable for fine-tuning.
        
        Args:
            format: Export format ('jsonl' or 'json')
            start_date: Filter messages after this date
            end_date: Filter messages before this date
            provider: Filter by LLM provider
            
        Returns:
            Formatted string ready for fine-tuning
        """
        messages = self.retrieve_messages(
            start_date=start_date,
            end_date=end_date,
            provider=provider
        )
        
        # Filter out messages without responses
        training_data = [
            {
                "messages": [
                    {"role": "user", "content": msg['user_message']},
                    {"role": "assistant", "content": msg['bot_response']}
                ]
            }
            for msg in messages
            if msg.get('bot_response')
        ]
        
        if format == "jsonl":
            # JSONL format (one JSON object per line)
            return "\n".join([json.dumps(item) for item in training_data])
        else:
            # Standard JSON array
            return json.dumps(training_data, indent=2)

    def get_analytics(self) -> Dict:
        """Get analytics about logged messages."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # Messages by provider
            cursor.execute("""
                SELECT provider, COUNT(*) as count 
                FROM messages 
                WHERE provider IS NOT NULL
                GROUP BY provider
            """)
            by_provider = dict(cursor.fetchall())
            
            # Messages by date (last 30 days)
            cursor.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as count 
                FROM messages 
                WHERE timestamp >= DATE('now', '-30 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """)
            by_date = dict(cursor.fetchall())
            
            # Average tokens used
            cursor.execute("""
                SELECT AVG(tokens_used) 
                FROM messages 
                WHERE tokens_used IS NOT NULL
            """)
            avg_tokens = cursor.fetchone()[0] or 0
            
            return {
                "total_messages": total_messages,
                "by_provider": by_provider,
                "by_date": by_date,
                "avg_tokens_used": round(avg_tokens, 2)
            }

    def delete_old_messages(self, days: int = 90):
        """Delete messages older than specified days."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM messages 
                WHERE timestamp < DATE('now', '-' || ? || ' days')
            """, (days,))
            conn.commit()
            return cursor.rowcount
