#!/usr/bin/env python3
"""
Test DigitalOcean Integration

Quick test script to verify DigitalOcean agent is properly configured.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.digitalocean import test_connection, get_agent


async def test_digitalocean():
    """Test DigitalOcean agent connection and functionality."""
    
    print("=" * 60)
    print("DigitalOcean Gradient AI Platform - Integration Test")
    print("=" * 60)
    print()
    
    # Test 1: Check configuration
    print("Test 1: Checking Configuration...")
    agent = get_agent()
    print(f"  ✓ Agent enabled: {agent.enabled}")
    print(f"  ✓ API token configured: {bool(agent.api_token)}")
    print(f"  ✓ Agent URL: {agent.agent_url if agent.agent_url else 'Not set'}")
    print(f"  ✓ Priority: {agent.priority}")
    print()
    
    if not agent.enabled:
        print("⚠️  DigitalOcean agent is disabled.")
        print("   Set DIGITALOCEAN_AGENT_ENABLED=true in .env")
        return
    
    if not agent.api_token or not agent.agent_url:
        print("⚠️  DigitalOcean agent not fully configured.")
        print("   Check DIGITALOCEAN_API_TOKEN and DIGITALOCEAN_AGENT_URL in .env")
        return
    
    # Test 2: Connection test
    print("Test 2: Testing Connection...")
    result = await test_connection()
    print(f"  Status: {result.get('status')}")
    print(f"  Message: {result.get('message')}")
    if 'response_time' in result:
        print(f"  Response time: {result['response_time']}s")
    if 'sample_response' in result:
        print(f"  Sample: {result['sample_response'][:80]}...")
    print()
    
    if result.get('status') != 'success':
        print("❌ Connection test failed!")
        if 'error' in result:
            print(f"   Error: {result['error']}")
        return
    
    # Test 3: Chat completion
    print("Test 3: Testing Chat Completion...")
    try:
        response = await agent.chat_completion(
            prompt="What is the capital of France?",
            context={"test": "integration_test"},
            stream=False
        )
        
        if response:
            print(f"  ✓ Response received: {response[:100]}...")
        else:
            print("  ❌ No response received")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()
    
    # Test 4: Cost estimation
    print("Test 4: Testing Cost Estimation...")
    try:
        cost = agent.get_cost_estimate(500, 300)
        print(f"  Input tokens: {cost['input_tokens']}")
        print(f"  Output tokens: {cost['output_tokens']}")
        print(f"  Total cost: ${cost['total_cost']:.6f}")
        
        monthly = agent.estimate_monthly_cost(
            requests_per_day=1000,
            avg_input_tokens=500,
            avg_output_tokens=300
        )
        print(f"  Monthly estimate (1000 req/day): ${monthly['estimated_cost']:.2f}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()
    
    print("=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_digitalocean())
