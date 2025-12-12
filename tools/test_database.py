#!/usr/bin/env python3
"""
Database Test Script

Verify database connection and basic operations.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_manager, Message, APIToken
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database():
    """Test database connection and operations."""
    
    print("=" * 60)
    print("BabbleBeaver Database Test")
    print("=" * 60)
    print()
    
    # Test 1: Database Configuration
    print("Test 1: Database Configuration")
    print(f"  Database Type: {db_manager.db_type}")
    print(f"  Database URL: {db_manager.database_url}")
    print("  ✓ Configuration loaded")
    print()
    
    # Test 2: Connection Test
    print("Test 2: Connection Test")
    try:
        with db_manager.get_session() as session:
            # Try a simple query
            count = session.query(Message).count()
            print(f"  Messages count: {count}")
            print("  ✓ Connection successful")
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return False
    print()
    
    # Test 3: Message Operations
    print("Test 3: Message Operations")
    try:
        with db_manager.get_session() as session:
            # Create a test message
            test_msg = Message(
                timestamp=datetime.utcnow(),
                user_message="Test message",
                bot_response="Test response",
                provider="test",
                model="test-model",
                tokens_used=100,
                metadata={"test": True}
            )
            session.add(test_msg)
            session.flush()
            msg_id = test_msg.id
            print(f"  Created message ID: {msg_id}")
            
            # Read it back
            retrieved = session.query(Message).filter(Message.id == msg_id).first()
            if retrieved:
                print(f"  Retrieved message: {retrieved.user_message}")
                print("  ✓ Message create/read works")
            else:
                print("  ✗ Could not retrieve message")
                return False
    except Exception as e:
        print(f"  ✗ Message operations failed: {e}")
        return False
    print()
    
    # Test 4: Token Operations
    print("Test 4: Token Operations")
    try:
        with db_manager.get_session() as session:
            # Create a test token
            test_token = APIToken(
                token_hash="test_hash_" + str(datetime.utcnow().timestamp()),
                description="Test token",
                created_at=datetime.utcnow(),
                is_active=True
            )
            session.add(test_token)
            session.flush()
            token_id = test_token.id
            print(f"  Created token ID: {token_id}")
            
            # Read it back
            retrieved = session.query(APIToken).filter(APIToken.id == token_id).first()
            if retrieved:
                print(f"  Retrieved token: {retrieved.description}")
                print("  ✓ Token create/read works")
            else:
                print("  ✗ Could not retrieve token")
                return False
    except Exception as e:
        print(f"  ✗ Token operations failed: {e}")
        return False
    print()
    
    # Test 5: Cleanup test data
    print("Test 5: Cleanup")
    try:
        with db_manager.get_session() as session:
            # Delete test message
            session.query(Message).filter(
                Message.user_message == "Test message"
            ).delete()
            
            # Delete test token
            session.query(APIToken).filter(
                APIToken.description == "Test token"
            ).delete()
            
            print("  ✓ Test data cleaned up")
    except Exception as e:
        print(f"  ⚠  Cleanup warning: {e}")
    print()
    
    # Summary
    print("=" * 60)
    print("✓ All database tests passed!")
    print("=" * 60)
    print()
    print("Database is ready to use.")
    print()
    
    return True


if __name__ == '__main__':
    try:
        success = test_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
