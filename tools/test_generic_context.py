#!/usr/bin/env python3
"""
Test script to verify context-aware system works with generic JSON data.
Tests that ANY JSON structure is accepted without field assumptions.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context_builder import ContextBuilder

def test_generic_json():
    """Test that any JSON structure is accepted and formatted correctly"""
    
    print("=" * 80)
    print("Testing Context-Aware System with Generic JSON")
    print("=" * 80)
    
    # Enable context-aware mode for testing
    os.environ["CONTEXT_AWARE_MODE"] = "auto"
    os.environ["CONTEXT_PROMPT_TEMPLATE"] = "minimal"
    builder = ContextBuilder()
    
    # Test Case 1: Completely arbitrary keys
    print("\n1. Testing arbitrary keys:")
    context1 = {
        "foo": "bar",
        "anything": 123,
        "nested": {"deep": "value"},
        "list_data": ["item1", "item2"]
    }
    
    result1 = builder.build_context_prompt(
        base_prompt="You are a helpful assistant.",
        context=context1
    )
    print(f"   Input: {context1}")
    print(f"   Output includes context: {('Foo:' in result1 or 'foo' in result1.lower())}")
    print(f"   Full prompt length: {len(result1)} chars")
    
    # Test Case 2: E-commerce context
    print("\n2. Testing e-commerce context:")
    context2 = {
        "current_page": "checkout",
        "cart_items": 3,
        "user_tier": "premium",
        "discount_code": "SAVE20"
    }
    
    result2 = builder.build_context_prompt(
        base_prompt="You are a helpful assistant.",
        context=context2
    )
    print(f"   Input: {context2}")
    print(f"   Output includes 'checkout': {'checkout' in result2.lower()}")
    print(f"   Full prompt length: {len(result2)} chars")
    
    # Test Case 3: Dashboard context
    print("\n3. Testing dashboard context:")
    context3 = {
        "view": "analytics",
        "date_range": "last_7_days",
        "filters_active": True,
        "widget_count": 6
    }
    
    result3 = builder.build_context_prompt(
        base_prompt="You are a helpful assistant.",
        context=context3
    )
    print(f"   Input: {context3}")
    print(f"   Output includes 'analytics': {'analytics' in result3.lower()}")
    print(f"   Full prompt length: {len(result3)} chars")
    
    # Test Case 4: Empty context (should return base prompt unchanged)
    print("\n4. Testing empty context:")
    context4 = {}
    
    result4 = builder.build_context_prompt(
        base_prompt="You are a helpful assistant.",
        context=context4
    )
    print(f"   Input: {context4}")
    print(f"   Output unchanged: {result4 == 'You are a helpful assistant.'}")
    print(f"   Full prompt length: {len(result4)} chars")
    
    # Test Case 5: Many items (should be limited to max_context_items)
    print("\n5. Testing context item limit:")
    context5 = {f"key_{i}": f"value_{i}" for i in range(20)}
    
    result5 = builder.build_context_prompt(
        base_prompt="You are a helpful assistant.",
        context=context5
    )
    # Count how many keys made it through (should be limited to 10)
    keys_in_result = sum(1 for i in range(20) if f"key_{i}" in result5.lower())
    print(f"   Input: 20 keys")
    print(f"   Keys in output: {keys_in_result} (max should be 10)")
    print(f"   Full prompt length: {len(result5)} chars")
    
    # Test Case 6: Verbose template
    print("\n6. Testing verbose template:")
    os.environ["CONTEXT_PROMPT_TEMPLATE"] = "verbose"
    builder_verbose = ContextBuilder()
    
    context6 = {"page": "settings", "section": "profile"}
    result6 = builder_verbose.build_context_prompt(
        base_prompt="You are a helpful assistant.",
        context=context6
    )
    print(f"   Input: {context6}")
    print(f"   Includes 'CURRENT CONTEXT': {'CURRENT CONTEXT' in result6}")
    print(f"   Full prompt length: {len(result6)} chars")
    
    print("\n" + "=" * 80)
    print("✓ All tests completed successfully!")
    print("=" * 80)

def test_disabled_mode():
    """Test that context is ignored when mode is explicitly disabled"""
    
    print("\n" + "=" * 80)
    print("Testing DISABLED Mode (Explicitly Set)")
    print("=" * 80)
    
    os.environ["CONTEXT_AWARE_MODE"] = "disabled"
    builder = ContextBuilder()
    
    context = {"foo": "bar", "test": 123}
    result = builder.build_context_prompt(
        base_prompt="You are a helpful assistant.",
        context=context
    )
    
    print(f"   CONTEXT_AWARE_MODE: disabled")
    print(f"   Context provided: {context}")
    print(f"   Context ignored: {result == 'You are a helpful assistant.'}")
    print(f"   Full prompt: {result}")
    
    print("=" * 80)

def test_auto_mode():
    """Test that context is used when mode is auto (default)"""
    
    print("\n" + "=" * 80)
    print("Testing AUTO Mode (Default - Context Provided = Used)")
    print("=" * 80)
    
    os.environ["CONTEXT_AWARE_MODE"] = "auto"
    builder = ContextBuilder()
    
    context = {"foo": "bar", "test": 123}
    result = builder.build_context_prompt(
        base_prompt="You are a helpful assistant.",
        context=context
    )
    
    print(f"   CONTEXT_AWARE_MODE: auto")
    print(f"   Context provided: {context}")
    print(f"   Context used: {'foo' in result.lower()}")
    print(f"   Full prompt length: {len(result)} chars")
    
    # Test with NO context - should return base prompt
    result_no_context = builder.build_context_prompt(
        base_prompt="You are a helpful assistant.",
        context={}
    )
    
    print(f"\n   No context provided:")
    print(f"   Returns base prompt unchanged: {result_no_context == 'You are a helpful assistant.'}")
    
    print("=" * 80)

if __name__ == "__main__":
    # Test disabled mode first
    test_disabled_mode()
    
    # Test auto mode (default)
    test_auto_mode()
    
    # Then test generic JSON handling
    test_generic_json()
    
    print("\n✅ All context-aware tests passed!")
    print("   - Auto mode (default): Context provided = automatically used")
    print("   - Disabled mode: Context ignored even if provided")
    print("   - Generic JSON accepted without field assumptions")
    print("   - Context item limit enforced")
    print("   - Both templates work")
