"""
API Token Manager - Database-backed token storage and validation
No JWT - Simple API tokens stored in SQLite database
"""

import sqlite3
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging
import os

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages API tokens with database storage (no JWT)."""
    
    def __init__(self, db_path: str = "db/tokens.db"):
        """
        Initialize token manager with SQLite database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema if it doesn't exist."""
        # Create db directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1,
                last_used_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Token database initialized at {self.db_path}")
    
    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def create_token(
        self,
        description: str = "API Access Token",
        expires_days: Optional[int] = 365
    ) -> Dict[str, str]:
        """
        Create a new API token.
        
        Args:
            description: Human-readable description of the token
            expires_days: Number of days until expiration (None = never expires)
            
        Returns:
            Dict with token and metadata
        """
        # Generate random token (44 chars, URL-safe)
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        
        created_at = datetime.utcnow().isoformat()
        expires_at = None
        if expires_days:
            expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO tokens (token_hash, description, created_at, expires_at, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (token_hash, description, created_at, expires_at))
            
            token_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Created token {token_id}: {description}")
            
            return {
                "token": token,  # Return plain token ONCE
                "id": token_id,
                "description": description,
                "created_at": created_at,
                "expires_at": expires_at
            }
            
        except sqlite3.IntegrityError:
            logger.error("Token hash collision (extremely rare)")
            # Retry with new token
            return self.create_token(description, expires_days)
        finally:
            conn.close()
    
    def verify_token(self, token: str) -> bool:
        """
        Verify if a token is valid and active.
        
        Args:
            token: Plain text token to verify
            
        Returns:
            True if token is valid and active, False otherwise
        """
        token_hash = self._hash_token(token)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, expires_at, is_active FROM tokens
            WHERE token_hash = ?
        """, (token_hash,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        token_id, expires_at, is_active = result
        
        # Check if active
        if not is_active:
            conn.close()
            return False
        
        # Check if expired
        if expires_at:
            expiry = datetime.fromisoformat(expires_at)
            if datetime.utcnow() > expiry:
                conn.close()
                return False
        
        # Update last_used_at
        cursor.execute("""
            UPDATE tokens SET last_used_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), token_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    def list_tokens(self) -> List[Dict]:
        """
        List all tokens (excluding token values).
        
        Returns:
            List of token metadata dicts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, description, created_at, expires_at, is_active, last_used_at
            FROM tokens
            ORDER BY created_at DESC
        """)
        
        tokens = []
        for row in cursor.fetchall():
            token_id, description, created_at, expires_at, is_active, last_used_at = row
            
            # Check if expired
            is_expired = False
            if expires_at:
                expiry = datetime.fromisoformat(expires_at)
                is_expired = datetime.utcnow() > expiry
            
            tokens.append({
                "id": token_id,
                "description": description,
                "created_at": created_at,
                "expires_at": expires_at,
                "is_active": bool(is_active),
                "is_expired": is_expired,
                "last_used_at": last_used_at
            })
        
        conn.close()
        return tokens
    
    def revoke_token(self, token_id: int) -> bool:
        """
        Revoke a token (mark as inactive).
        
        Args:
            token_id: ID of token to revoke
            
        Returns:
            True if revoked, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tokens SET is_active = 0
            WHERE id = ?
        """, (token_id,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            logger.info(f"Revoked token {token_id}")
            return True
        
        return False
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens from database (housekeeping)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            DELETE FROM tokens
            WHERE expires_at IS NOT NULL AND expires_at < ?
        """, (now,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired tokens")


# Global instance
token_manager = TokenManager()
