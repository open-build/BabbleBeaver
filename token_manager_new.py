"""
Token Manager - Database-backed API token storage

Uses SQLAlchemy ORM for database abstraction.
Supports SQLite (development) and PostgreSQL (production).
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging
from database import db_manager, APIToken

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Manages API tokens with database storage (no JWT).
    
    Automatically uses SQLite or PostgreSQL based on DATABASE_URL environment variable.
    """
    
    def __init__(self):
        """Initialize token manager with database manager."""
        self.db_manager = db_manager
        logger.info(f"TokenManager initialized with {self.db_manager.db_type} database")
    
    def _hash_token(self, token: str) -> str:
        """Hash a token using SHA256."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def create_token(
        self,
        description: str = "API Token",
        expires_days: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Generate a new API token.
        
        Args:
            description: Human-readable description
            expires_days: Days until expiration (None = never expires)
            
        Returns:
            Dictionary with token (plaintext, show once) and token_id
        """
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        
        # Calculate expiration date
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        try:
            with self.db_manager.get_session() as session:
                api_token = APIToken(
                    token_hash=token_hash,
                    description=description,
                    created_at=datetime.utcnow(),
                    expires_at=expires_at,
                    is_active=True
                )
                session.add(api_token)
                session.flush()  # Get the ID before commit
                token_id = api_token.id
                
                logger.info(f"Created API token ID {token_id}: {description}")
                
                return {
                    'token': token,  # Only shown once!
                    'token_id': token_id,
                    'description': description,
                    'expires_at': expires_at.isoformat() if expires_at else None
                }
                
        except Exception as e:
            logger.error(f"Error creating token: {e}")
            raise
    
    def verify_token(self, token: str) -> bool:
        """
        Verify if a token is valid and active.
        
        Args:
            token: Token to verify (plaintext)
            
        Returns:
            True if valid, False otherwise
        """
        token_hash = self._hash_token(token)
        
        try:
            with self.db_manager.get_session() as session:
                api_token = session.query(APIToken).filter(
                    APIToken.token_hash == token_hash,
                    APIToken.is_active == True
                ).first()
                
                if not api_token:
                    return False
                
                # Check if expired
                if api_token.expires_at:
                    if datetime.utcnow() > api_token.expires_at:
                        logger.debug(f"Token ID {api_token.id} has expired")
                        return False
                
                # Update last used timestamp
                api_token.last_used_at = datetime.utcnow()
                # Session will auto-commit due to context manager
                
                logger.debug(f"Token ID {api_token.id} verified successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return False
    
    def list_tokens(self) -> List[Dict]:
        """
        List all tokens (without showing actual token values).
        
        Returns:
            List of token info dictionaries
        """
        try:
            with self.db_manager.get_session() as session:
                tokens = session.query(APIToken).order_by(
                    APIToken.created_at.desc()
                ).all()
                
                return [token.to_dict() for token in tokens]
                
        except Exception as e:
            logger.error(f"Error listing tokens: {e}")
            raise
    
    def revoke_token(self, token_id: int) -> bool:
        """
        Revoke (deactivate) a token.
        
        Args:
            token_id: ID of token to revoke
            
        Returns:
            True if revoked, False if not found
        """
        try:
            with self.db_manager.get_session() as session:
                api_token = session.query(APIToken).filter(
                    APIToken.id == token_id
                ).first()
                
                if not api_token:
                    logger.warning(f"Token ID {token_id} not found")
                    return False
                
                api_token.is_active = False
                logger.info(f"Revoked token ID {token_id}: {api_token.description}")
                return True
                
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            raise
    
    def delete_expired_tokens(self) -> int:
        """
        Delete expired tokens from database.
        
        Returns:
            Number of tokens deleted
        """
        try:
            now = datetime.utcnow()
            
            with self.db_manager.get_session() as session:
                deleted = session.query(APIToken).filter(
                    APIToken.expires_at.isnot(None),
                    APIToken.expires_at < now
                ).delete()
                
                logger.info(f"Deleted {deleted} expired tokens")
                return deleted
                
        except Exception as e:
            logger.error(f"Error deleting expired tokens: {e}")
            raise
    
    def get_token_info(self, token_id: int) -> Optional[Dict]:
        """
        Get information about a specific token.
        
        Args:
            token_id: Token ID
            
        Returns:
            Token info dictionary or None
        """
        try:
            with self.db_manager.get_session() as session:
                api_token = session.query(APIToken).filter(
                    APIToken.id == token_id
                ).first()
                
                return api_token.to_dict() if api_token else None
                
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            raise


# Global token manager instance
token_manager = TokenManager()
