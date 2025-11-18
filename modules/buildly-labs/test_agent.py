"""
Test script for Buildly Labs Agent

This script demonstrates how the agent works and can be used to test
the module independently.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from buildly_labs.buildly_agent import BuildlyAgent, enrich_user_message


async def test_agent():
    """Test the Buildly Labs agent functionality."""
    
    print("=" * 60)
    print("BUILDLY LABS AGENT TEST")
    print("=" * 60)
    print()
    
    # Create agent instance
    agent = BuildlyAgent()
    
    print(f"Agent Enabled: {agent.enabled}")
    print(f"Base URL: {agent.base_url}")
    print(f"Timeout: {agent.timeout}s")
    print()
    
    # Test UUID extraction
    print("-" * 60)
    print("TEST 1: UUID Extraction")
    print("-" * 60)
    
    test_messages = [
        "Tell me about product_uuid: 123e4567-e89b-12d3-a456-426614174000",
        "What features does product_uuid=abc12345-1234-5678-90ab-cdef12345678 have?",
        'Check out "product_uuid": "f47ac10b-58cc-4372-a567-0e02b2c3d479"',
        "No UUID in this message"
    ]
    
    for msg in test_messages:
        uuid = BuildlyAgent.extract_product_uuid(msg)
        print(f"Message: {msg[:50]}...")
        print(f"Extracted UUID: {uuid}")
        print()
    
    # Test enrichment with a sample UUID
    print("-" * 60)
    print("TEST 2: Message Enrichment")
    print("-" * 60)
    
    sample_uuid = "123e4567-e89b-12d3-a456-426614174000"
    sample_message = f"What are the latest features? product_uuid: {sample_uuid}"
    
    print(f"Original Message: {sample_message}")
    print()
    print("Fetching product context...")
    
    enriched, context = await enrich_user_message(sample_message)
    
    print()
    print(f"Enrichment Status: {'Success' if context.get('enabled') else 'Disabled'}")
    
    if context.get('product_uuid'):
        print(f"Product UUID: {context['product_uuid']}")
        print(f"Product Info: {context.get('product_info', 'Not found')}")
        print(f"Features Count: {len(context.get('features', [])) if context.get('features') else 0}")
        print(f"Releases Count: {len(context.get('releases', [])) if context.get('releases') else 0}")
    
    print()
    print("-" * 60)
    print("ENRICHED MESSAGE:")
    print("-" * 60)
    print(enriched)
    print()
    
    # Test with explicit UUID parameter
    print("-" * 60)
    print("TEST 3: Explicit UUID Parameter")
    print("-" * 60)
    
    message_without_uuid = "What's new in the latest release?"
    explicit_uuid = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    
    print(f"Message: {message_without_uuid}")
    print(f"Explicit UUID: {explicit_uuid}")
    print()
    
    enriched, context = await enrich_user_message(message_without_uuid, explicit_uuid)
    
    print(f"Enrichment Status: {'Success' if context.get('product_uuid') else 'Skipped'}")
    print()
    
    # Performance test
    print("-" * 60)
    print("TEST 4: Performance Test")
    print("-" * 60)
    
    import time
    
    test_uuid = "abc12345-1234-5678-90ab-cdef12345678"
    test_message = f"Performance test with product_uuid: {test_uuid}"
    
    start_time = time.time()
    enriched, context = await enrich_user_message(test_message)
    elapsed = time.time() - start_time
    
    print(f"Time taken: {elapsed:.2f} seconds")
    print(f"Status: {'✓ Success' if elapsed < 6 else '✗ Timeout'}")
    print()
    
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_agent())
