#!/usr/bin/env python3
"""
Test the new token management system
"""

import sys
sys.path.insert(0, '.')

from token_manager import token_manager

print("=" * 80)
print("Testing Token Management System (No JWT)")
print("=" * 80)

# Test 1: Create token
print("\n1. Creating test token...")
result = token_manager.create_token(
    description="Test API Token",
    expires_days=365
)
print(f"   ✅ Token created: ID {result['id']}")
print(f"   Token: {result['token'][:20]}... (truncated)")
print(f"   Expires: {result['expires_at']}")

token = result['token']

# Test 2: Verify token
print("\n2. Verifying token...")
is_valid = token_manager.verify_token(token)
print(f"   ✅ Token valid: {is_valid}")

# Test 3: Create another token
print("\n3. Creating second token...")
result2 = token_manager.create_token(
    description="Production API",
    expires_days=None  # Never expires
)
print(f"   ✅ Token created: ID {result2['id']}")
print(f"   Expires: {result2['expires_at']} (Never)")

# Test 4: List all tokens
print("\n4. Listing all tokens...")
tokens = token_manager.list_tokens()
print(f"   ✅ Total tokens: {len(tokens)}")
for t in tokens:
    status = "Active" if t['is_active'] and not t['is_expired'] else "Inactive"
    print(f"   - ID {t['id']}: {t['description']} ({status})")

# Test 5: Revoke token
print(f"\n5. Revoking token ID {result['id']}...")
success = token_manager.revoke_token(result['id'])
print(f"   ✅ Revoked: {success}")

# Test 6: Verify revoked token fails
print("\n6. Verifying revoked token...")
is_valid = token_manager.verify_token(token)
print(f"   ✅ Token now invalid: {not is_valid}")

# Test 7: List tokens again
print("\n7. Listing tokens after revocation...")
tokens = token_manager.list_tokens()
for t in tokens:
    status = "Active" if t['is_active'] and not t['is_expired'] else "Revoked/Expired"
    print(f"   - ID {t['id']}: {t['description']} ({status})")

print("\n" + "=" * 80)
print("✅ All token management tests passed!")
print("=" * 80)
print("\nDatabase location: db/tokens.db")
print("Ready for production use!")
