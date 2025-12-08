#!/usr/bin/env python3
"""
Performance comparison: Context Hash vs Plain Text History

This script demonstrates the actual performance impact of using
context hashing vs sending full conversation history.
"""

import json
import time
import sys
from typing import Dict, List

def simulate_plain_text_request(history: Dict[str, List[str]], message: str) -> int:
    """Simulate sending full history in request."""
    request_data = {
        "message": message,
        "history": history
    }
    json_str = json.dumps(request_data)
    return len(json_str.encode('utf-8'))

def simulate_hash_request(context_hash: str, message: str) -> int:
    """Simulate sending context hash in request."""
    request_data = {
        "message": message,
        "context_hash": context_hash
    }
    json_str = json.dumps(request_data)
    return len(json_str.encode('utf-8'))

def run_comparison():
    """Run performance comparison."""
    print("=" * 70)
    print("CONTEXT HASH vs PLAIN TEXT PERFORMANCE COMPARISON")
    print("=" * 70)
    print()
    
    # Simulate conversation growth
    scenarios = [
        (0, "Initial message"),
        (2, "After 2 exchanges"),
        (5, "After 5 exchanges"),
        (10, "After 10 exchanges"),
        (20, "After 20 exchanges"),
        (50, "After 50 exchanges")
    ]
    
    # Simulate context hash (always 16 chars)
    context_hash = "a1b2c3d4e5f6g7h8"
    test_message = "What features does this product have?"
    
    print(f"Test Message: '{test_message}'")
    print(f"Context Hash: '{context_hash}' (16 bytes)")
    print()
    print("-" * 70)
    
    for exchanges, label in scenarios:
        # Build history
        history = {
            "user": [f"User message {i+1}" for i in range(exchanges)],
            "bot": [f"Bot response {i+1} with some detailed explanation about the topic being discussed." for i in range(exchanges)]
        }
        
        plain_size = simulate_plain_text_request(history, test_message)
        hash_size = simulate_hash_request(context_hash, test_message)
        
        reduction = ((plain_size - hash_size) / plain_size * 100) if plain_size > 0 else 0
        
        print(f"\n{label}:")
        print(f"  Plain Text Approach: {plain_size:,} bytes")
        print(f"  Context Hash Approach: {hash_size:,} bytes")
        print(f"  Savings: {plain_size - hash_size:,} bytes ({reduction:.1f}% reduction)")
        
        if plain_size > hash_size:
            print(f"  ✅ Context hash is {plain_size / hash_size:.1f}x more efficient")
        else:
            print(f"  ⚠️  Context hash is NOT more efficient at this scale")
    
    print()
    print("=" * 70)
    print("NETWORK TRANSFER TIME ESTIMATE (assuming 1 Mbps connection)")
    print("=" * 70)
    
    # Simulate 10-exchange conversation
    history = {
        "user": [f"User message {i+1}" for i in range(10)],
        "bot": [f"Bot response {i+1} with detailed explanation." for i in range(10)]
    }
    
    plain_size = simulate_plain_text_request(history, test_message)
    hash_size = simulate_hash_request(context_hash, test_message)
    
    # 1 Mbps = 125,000 bytes/sec
    bytes_per_ms = 125000 / 1000
    
    plain_time = plain_size / bytes_per_ms
    hash_time = hash_size / bytes_per_ms
    
    print(f"\nPlain Text: {plain_size} bytes = {plain_time:.2f}ms transfer time")
    print(f"Context Hash: {hash_size} bytes = {hash_time:.2f}ms transfer time")
    print(f"Time saved: {plain_time - hash_time:.2f}ms ({(plain_time - hash_time) / plain_time * 100:.1f}%)")
    
    print()
    print("=" * 70)
    print("WHEN TO USE CONTEXT HASH:")
    print("=" * 70)
    print()
    print("✅ Use context hash when:")
    print("   - Conversation has >2 exchanges (messages)")
    print("   - Mobile/low-bandwidth users")
    print("   - High traffic applications")
    print("   - Cost optimization important")
    print()
    print("❌ DON'T use context hash when:")
    print("   - Single message (no history)")
    print("   - Stateless requests")
    print("   - Server memory constrained")
    print()
    print("💡 RECOMMENDATION:")
    print("   Make it OPTIONAL - let frontend decide based on their needs")
    print("=" * 70)

if __name__ == "__main__":
    run_comparison()
