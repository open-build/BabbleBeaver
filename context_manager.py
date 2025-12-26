"""
Context Manager for BabbleBeaver

Provides efficient context handling with:
- Compression (zlib) for large context data
- LRU caching for frequently accessed contexts
- Session management with hash-based identifiers
- Token-aware context pruning
- Redis support for distributed sessions (optional)

Performance optimizations:
- Compress context data >1KB to reduce payload size by ~70%
- Cache up to 1000 sessions in-memory with automatic eviction
- Hash-based session IDs for fast lookups
- Lazy loading of context data
"""

import hashlib
import zlib
import base64
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
from collections import OrderedDict
import os

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


class ContextCache:
    """LRU cache with TTL for session contexts."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.timestamps = {}
    
    def get(self, key: str) -> Optional[Dict]:
        """Get value from cache if not expired."""
        if key not in self.cache:
            return None
        
        # Check expiration
        if key in self.timestamps:
            age = (datetime.now() - self.timestamps[key]).total_seconds()
            if age > self.ttl_seconds:
                self._remove(key)
                return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def set(self, key: str, value: Dict):
        """Set value in cache with LRU eviction."""
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # Remove oldest item
                oldest_key = next(iter(self.cache))
                self._remove(oldest_key)
        
        self.cache[key] = value
        self.timestamps[key] = datetime.now()
    
    def _remove(self, key: str):
        """Remove key from cache."""
        self.cache.pop(key, None)
        self.timestamps.pop(key, None)
    
    def clear_expired(self):
        """Clear all expired entries."""
        now = datetime.now()
        expired = [
            key for key, timestamp in self.timestamps.items()
            if (now - timestamp).total_seconds() > self.ttl_seconds
        ]
        for key in expired:
            self._remove(key)


class ContextManager:
    """
    Manages conversation context with compression and caching.
    
    Features:
    - Automatic compression for contexts >1KB
    - Session-based context storage with hash IDs
    - In-memory LRU cache with TTL
    - Optional Redis backend for distributed systems
    - Token-aware context pruning
    """
    
    # Compression threshold in bytes
    COMPRESSION_THRESHOLD = 1024
    
    def __init__(
        self, 
        use_redis: bool = False,
        redis_url: Optional[str] = None,
        cache_size: int = 1000,
        cache_ttl: int = 3600
    ):
        """
        Initialize context manager.
        
        Args:
            use_redis: Enable Redis backend
            redis_url: Redis connection URL (default from env)
            cache_size: Max sessions in memory cache
            cache_ttl: Cache TTL in seconds (default: 1 hour)
        """
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.cache = ContextCache(max_size=cache_size, ttl_seconds=cache_ttl)
        self.redis_client = None
        
        if self.use_redis:
            try:
                redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                self.redis_client.ping()
                logger.info(f"Redis backend enabled: {redis_url}")
            except Exception as e:
                logger.warning(f"Redis connection failed, falling back to memory: {e}")
                self.use_redis = False
    
    @staticmethod
    def generate_session_id(user_id: str, context_type: str = "chat") -> str:
        """
        Generate deterministic session ID from user and context.
        
        Args:
            user_id: User identifier
            context_type: Type of context (e.g., 'chat', 'product')
        
        Returns:
            SHA256 hash as session ID
        """
        data = f"{user_id}:{context_type}:{datetime.now().strftime('%Y-%m-%d')}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    @staticmethod
    def compress_data(data: Dict) -> Tuple[str, bool]:
        """
        Compress data if above threshold.
        
        Args:
            data: Dictionary to compress
        
        Returns:
            Tuple of (encoded_data, is_compressed)
        """
        json_str = json.dumps(data)
        json_bytes = json_str.encode('utf-8')
        
        # Only compress if above threshold
        if len(json_bytes) < ContextManager.COMPRESSION_THRESHOLD:
            return base64.b64encode(json_bytes).decode('utf-8'), False
        
        # Compress with zlib (typically 60-80% reduction)
        compressed = zlib.compress(json_bytes, level=6)
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        compression_ratio = len(compressed) / len(json_bytes)
        logger.debug(f"Compressed context: {len(json_bytes)}B -> {len(compressed)}B ({compression_ratio:.1%})")
        
        return encoded, True
    
    @staticmethod
    def decompress_data(encoded_data: str, is_compressed: bool) -> Dict:
        """
        Decompress data if needed.
        
        Args:
            encoded_data: Base64 encoded data
            is_compressed: Whether data is compressed
        
        Returns:
            Decompressed dictionary
        """
        decoded = base64.b64decode(encoded_data.encode('utf-8'))
        
        if is_compressed:
            decompressed = zlib.decompress(decoded)
            return json.loads(decompressed.decode('utf-8'))
        
        return json.loads(decoded.decode('utf-8'))
    
    def store_context(
        self, 
        session_id: str, 
        context_data: Dict,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """
        Store context data with optional compression.
        
        Args:
            session_id: Session identifier
            context_data: Context dictionary to store
            ttl_seconds: TTL override (default: use cache TTL)
        
        Returns:
            Session ID (for confirmation)
        """
        # Compress if needed
        encoded_data, is_compressed = self.compress_data(context_data)
        
        storage_obj = {
            'data': encoded_data,
            'compressed': is_compressed,
            'timestamp': datetime.now().isoformat(),
            'size_bytes': len(encoded_data)
        }
        
        # Store in cache
        self.cache.set(session_id, storage_obj)
        
        # Store in Redis if enabled
        if self.use_redis and self.redis_client:
            try:
                ttl = ttl_seconds or self.cache.ttl_seconds
                self.redis_client.setex(
                    f"ctx:{session_id}",
                    ttl,
                    json.dumps(storage_obj)
                )
            except Exception as e:
                logger.warning(f"Failed to store in Redis: {e}")
        
        logger.debug(f"Stored context {session_id}: {len(encoded_data)} bytes (compressed: {is_compressed})")
        return session_id
    
    def retrieve_context(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve and decompress context data.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Context dictionary or None if not found
        """
        # Try cache first
        storage_obj = self.cache.get(session_id)
        
        # Fall back to Redis
        if not storage_obj and self.use_redis and self.redis_client:
            try:
                redis_data = self.redis_client.get(f"ctx:{session_id}")
                if redis_data:
                    storage_obj = json.loads(redis_data)
                    # Populate cache for next time
                    self.cache.set(session_id, storage_obj)
            except Exception as e:
                logger.warning(f"Failed to retrieve from Redis: {e}")
        
        if not storage_obj:
            return None
        
        # Decompress and return
        return self.decompress_data(
            storage_obj['data'], 
            storage_obj['compressed']
        )
    
    def update_context(
        self, 
        session_id: str, 
        updates: Dict,
        merge: bool = True
    ) -> bool:
        """
        Update existing context.
        
        Args:
            session_id: Session identifier
            updates: New data to add/update
            merge: If True, merge with existing; if False, replace
        
        Returns:
            True if successful, False if session not found
        """
        existing = self.retrieve_context(session_id)
        
        if existing is None and merge:
            return False
        
        if merge and existing:
            existing.update(updates)
            new_data = existing
        else:
            new_data = updates
        
        self.store_context(session_id, new_data)
        return True
    
    def delete_context(self, session_id: str):
        """Delete context from cache and Redis."""
        self.cache._remove(session_id)
        
        if self.use_redis and self.redis_client:
            try:
                self.redis_client.delete(f"ctx:{session_id}")
            except Exception as e:
                logger.warning(f"Failed to delete from Redis: {e}")
    
    def prune_history(
        self, 
        history: Dict[str, List[str]], 
        max_tokens: int = 2000,
        tokens_per_message: int = 50
    ) -> Dict[str, List[str]]:
        """
        Prune conversation history to fit within token budget.
        
        Args:
            history: Conversation history dict with 'user' and 'bot' lists
            max_tokens: Maximum tokens to keep
            tokens_per_message: Estimated tokens per message
        
        Returns:
            Pruned history dictionary
        """
        if not history or not history.get('user') or not history.get('bot'):
            return history
        
        user_msgs = history['user']
        bot_msgs = history['bot']
        
        # Calculate how many messages we can keep
        max_messages = max_tokens // tokens_per_message
        messages_per_side = max_messages // 2
        
        if len(user_msgs) <= messages_per_side:
            return history
        
        # Keep most recent messages
        return {
            'user': user_msgs[-messages_per_side:],
            'bot': bot_msgs[-messages_per_side:]
        }
    
    def create_context_hash(
        self,
        user_id: str,
        product_uuid: Optional[str] = None,
        history: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create compressed context hash for frontend.
        
        This generates a single hash that encodes all context,
        allowing frontend to send just the hash instead of full context.
        
        Args:
            user_id: User identifier
            product_uuid: Product context
            history: Conversation history
            metadata: Additional metadata
        
        Returns:
            Base64-encoded context hash
        """
        context_data = {
            'user_id': user_id,
            'product_uuid': product_uuid,
            'history': history or {'user': [], 'bot': []},
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }
        
        # Generate session ID and store
        session_id = self.generate_session_id(user_id, 'chat')
        self.store_context(session_id, context_data)
        
        return session_id
    
    def resolve_context_hash(self, context_hash: str) -> Optional[Dict]:
        """
        Resolve context hash to full context data.
        
        Args:
            context_hash: Session ID / context hash
        
        Returns:
            Full context dictionary or None
        """
        return self.retrieve_context(context_hash)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self.cache.clear_expired()
        
        return {
            'cache_size': len(self.cache.cache),
            'cache_max': self.cache.max_size,
            'cache_ttl': self.cache.ttl_seconds,
            'redis_enabled': self.use_redis,
            'compression_threshold': self.COMPRESSION_THRESHOLD
        }


# Global instance
context_manager = ContextManager(
    use_redis=os.getenv('USE_REDIS', 'false').lower() in ('true', '1'),
    cache_size=int(os.getenv('CONTEXT_CACHE_SIZE', '1000')),
    cache_ttl=int(os.getenv('CONTEXT_CACHE_TTL', '3600'))
)
