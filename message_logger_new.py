"""
Message Logger - Database-backed chat log storage

Uses SQLAlchemy ORM for database abstraction.
Supports SQLite (development) and PostgreSQL (production).
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from database import db_manager, Message

logger = logging.getLogger(__name__)


class MessageLogger:
    """
    Log and retrieve chat messages with database persistence.
    
    Automatically uses SQLite or PostgreSQL based on DATABASE_URL environment variable.
    """
    
    def __init__(self):
        """Initialize message logger with database manager."""
        self.db_manager = db_manager
        logger.info(f"MessageLogger initialized with {self.db_manager.db_type} database")
    
    def log_message(
        self,
        message: str,
        response: str = "",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log a message and its response.
        
        Args:
            message: User message
            response: Bot response
            provider: LLM provider used (gemini, openai, digitalocean, etc.)
            model: Model name used
            tokens_used: Number of tokens consumed
            metadata: Additional metadata (dict)
            
        Returns:
            Message ID
        """
        try:
            with self.db_manager.get_session() as session:
                msg = Message(
                    timestamp=datetime.utcnow(),
                    user_message=message,
                    bot_response=response,
                    provider=provider,
                    model=model,
                    tokens_used=tokens_used,
                    metadata_=metadata or {}
                )
                session.add(msg)
                session.flush()  # Get the ID before commit
                message_id = msg.id
                
                logger.debug(f"Logged message ID {message_id}")
                return message_id
                
        except Exception as e:
            logger.error(f"Error logging message: {e}")
            raise
    
    def get_messages(
        self,
        limit: int = 100,
        offset: int = 0,
        provider: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve messages with optional filters.
        
        Args:
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            provider: Filter by provider
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            List of message dictionaries
        """
        try:
            with self.db_manager.get_session() as session:
                query = session.query(Message)
                
                # Apply filters
                if provider:
                    query = query.filter(Message.provider == provider)
                if start_date:
                    query = query.filter(Message.timestamp >= start_date)
                if end_date:
                    query = query.filter(Message.timestamp <= end_date)
                
                # Order by timestamp descending (newest first)
                query = query.order_by(Message.timestamp.desc())
                
                # Apply pagination
                query = query.limit(limit).offset(offset)
                
                messages = query.all()
                return [msg.to_dict() for msg in messages]
                
        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            raise
    
    def get_message_by_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific message by ID.
        
        Args:
            message_id: Message ID
            
        Returns:
            Message dictionary or None
        """
        try:
            with self.db_manager.get_session() as session:
                msg = session.query(Message).filter(Message.id == message_id).first()
                return msg.to_dict() if msg else None
                
        except Exception as e:
            logger.error(f"Error retrieving message {message_id}: {e}")
            raise
    
    def get_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about logged messages.
        
        Returns:
            Analytics dictionary with counts and averages
        """
        try:
            with self.db_manager.get_session() as session:
                from sqlalchemy import func
                
                # Total messages
                total_messages = session.query(func.count(Message.id)).scalar()
                
                # Messages per provider
                provider_counts = session.query(
                    Message.provider,
                    func.count(Message.id).label('count')
                ).group_by(Message.provider).all()
                
                # Average tokens
                avg_tokens = session.query(
                    func.avg(Message.tokens_used)
                ).filter(Message.tokens_used.isnot(None)).scalar()
                
                # Total tokens
                total_tokens = session.query(
                    func.sum(Message.tokens_used)
                ).filter(Message.tokens_used.isnot(None)).scalar()
                
                return {
                    'total_messages': total_messages or 0,
                    'providers': {
                        provider: count for provider, count in provider_counts
                    },
                    'average_tokens': float(avg_tokens) if avg_tokens else 0,
                    'total_tokens': int(total_tokens) if total_tokens else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            raise
    
    def delete_old_messages(self, days: int = 30) -> int:
        """
        Delete messages older than specified days.
        
        Args:
            days: Delete messages older than this many days
            
        Returns:
            Number of messages deleted
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            with self.db_manager.get_session() as session:
                deleted = session.query(Message).filter(
                    Message.timestamp < cutoff_date
                ).delete()
                
                logger.info(f"Deleted {deleted} messages older than {days} days")
                return deleted
                
        except Exception as e:
            logger.error(f"Error deleting old messages: {e}")
            raise
    
    def search_messages(
        self,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search messages by text content.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching message dictionaries
        """
        try:
            with self.db_manager.get_session() as session:
                # Use LIKE for simple text search
                # For PostgreSQL, could use full-text search
                search_pattern = f'%{query}%'
                
                messages = session.query(Message).filter(
                    (Message.user_message.like(search_pattern)) |
                    (Message.bot_response.like(search_pattern))
                ).order_by(Message.timestamp.desc()).limit(limit).all()
                
                return [msg.to_dict() for msg in messages]
                
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            raise


# Global message logger instance
message_logger = MessageLogger()
