"""
Simple API Key Authentication for BabbleBeaver.
Supports both environment variable token (legacy) and database-backed tokens.
"""

import os
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from token_manager import token_manager

# Legacy API key from environment (optional, for backward compatibility)
API_KEY = os.getenv("API_KEY")

# Admin credentials from environment  
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_admin_credentials(username: str, password: str) -> bool:
    """Verify admin username and password against environment variables."""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Dependency to verify API key from bearer token.
    Checks environment variable first (priority), then database.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User info dict
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    
    # PRIORITY 1: Check environment variable token (if configured)
    if API_KEY and token == API_KEY:
        return {"authenticated": True, "type": "api_key", "sub": "env_token"}
    
    # PRIORITY 2: Check database tokens
    if token_manager.verify_token(token):
        return {"authenticated": True, "type": "api_key", "sub": "api_access"}
    
    # Both checks failed
    raise HTTPException(
        status_code=401,
        detail="Invalid or expired API token"
    )


async def require_admin(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Dependency to require admin API key authentication.
    Same as get_current_user for simple API key auth.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User info dict
        
    Raises:
        HTTPException: If authentication fails
    """
    return await get_current_user(credentials)
