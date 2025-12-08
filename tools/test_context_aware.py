#!/usr/bin/env python3
"""
Test Context-Aware System

This script tests the context-aware functionality of BabbleBeaver.
"""

import requests
import json

# Configuration
API_URL = "http://localhost:8004"
API_KEY = "aVcAEKOmtrHh5JE0Ib1yomAewODjU6ZZ9ReBrNVXcck"  # Default from .env

def test_without_context():
    """Test chatbot without context - should give generic response."""
    print("\n" + "="*60)
    print("TEST 1: WITHOUT CONTEXT")
    print("="*60)
    
    response = requests.post(
        f"{API_URL}/chatbot",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "message": "What should I rename this product to?"
        }
    )
    
    data = response.json()
    print(f"\nQuestion: What should I rename this product to?")
    print(f"Response: {data['response'][:200]}...")
    print(f"\nProvider: {data.get('provider')}, Model: {data.get('model')}")
    

def test_with_context():
    """Test chatbot with context - should give specific response."""
    print("\n" + "="*60)
    print("TEST 2: WITH CONTEXT (Product Management Scenario)")
    print("="*60)
    
    response = requests.post(
        f"{API_URL}/chatbot",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "message": "What should I rename this product to?",
            "context": {
                "product_name": "Mobile App v2",
                "product_type": "ios_app",
                "current_page": "product_settings",
                "user_role": "product_owner",
                "workflow_step": "renaming"
            }
        }
    )
    
    data = response.json()
    print(f"\nQuestion: What should I rename this product to?")
    print(f"\nContext Provided:")
    print(f"  - Product: Mobile App v2 (iOS)")
    print(f"  - Page: product_settings")
    print(f"  - User Role: product_owner")
    print(f"\nResponse: {data['response'][:300]}...")
    print(f"\nProvider: {data.get('provider')}, Model: {data.get('model')}")


def test_with_buildly_context():
    """Test chatbot with Buildly-specific context."""
    print("\n" + "="*60)
    print("TEST 3: WITH BUILDLY CONTEXT (Real Product UUID)")
    print("="*60)
    
    response = requests.post(
        f"{API_URL}/chatbot",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "message": "What features does this product have?",
            "context": {
                "product_uuid": "your-product-uuid-here",  # Replace with real UUID
                "current_page": "product_overview",
                "user_role": "developer"
            }
        }
    )
    
    data = response.json()
    print(f"\nQuestion: What features does this product have?")
    print(f"\nContext Provided:")
    print(f"  - Product UUID: your-product-uuid-here")
    print(f"  - Page: product_overview")
    print(f"  - User Role: developer")
    print(f"\nResponse: {data['response'][:300]}...")
    
    if data.get('product_context'):
        print(f"\n✅ Product enrichment: {data['product_context']}")


def test_ecommerce_context():
    """Test chatbot with e-commerce context (different use case)."""
    print("\n" + "="*60)
    print("TEST 4: E-COMMERCE USE CASE")
    print("="*60)
    
    response = requests.post(
        f"{API_URL}/chatbot",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "message": "What would be a good name for this?",
            "context": {
                "product_type": "smartphone",
                "category": "electronics",
                "price_range": "premium",
                "target_audience": "professionals",
                "current_page": "product_catalog"
            }
        }
    )
    
    data = response.json()
    print(f"\nQuestion: What would be a good name for this?")
    print(f"\nContext Provided:")
    print(f"  - Product Type: smartphone")
    print(f"  - Category: electronics")
    print(f"  - Price Range: premium")
    print(f"  - Target Audience: professionals")
    print(f"\nResponse: {data['response'][:300]}...")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("BABBLEBEAVER CONTEXT-AWARE SYSTEM TEST")
    print("="*60)
    print("\nThis test demonstrates how BabbleBeaver uses context to provide")
    print("more relevant, specific responses.\n")
    
    try:
        # Run tests
        test_without_context()
        test_with_context()
        test_with_buildly_context()
        test_ecommerce_context()
        
        print("\n" + "="*60)
        print("✅ TESTS COMPLETE")
        print("="*60)
        print("\nNotice how responses change based on context!")
        print("The AI is now context-aware and adapts to different use cases.\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to BabbleBeaver")
        print("Make sure the server is running: uvicorn main:app --reload --port 8004\n")
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
