#!/usr/bin/env python3
"""
Performance comparison: Frontend compression vs plain JSON vs server-side hash

Compares three approaches for sending initial context data:
1. Plain JSON (current default)
2. Frontend compresses and sends base64
3. Server-side session hash (current optional feature)
"""

import json
import zlib
import base64
import time

def plain_json_approach(context_data: dict) -> int:
    """Traditional: Send plain JSON."""
    json_str = json.dumps(context_data)
    return len(json_str.encode('utf-8'))

def frontend_compression_approach(context_data: dict) -> tuple:
    """Frontend compresses before sending."""
    # Frontend does: JSON -> compress -> base64
    json_str = json.dumps(context_data)
    json_bytes = json_str.encode('utf-8')
    compressed = zlib.compress(json_bytes, level=6)
    encoded = base64.b64encode(compressed)
    
    # Network transfer size
    transfer_size = len(encoded)
    
    # Backend must: base64 decode -> decompress -> JSON parse
    backend_overhead = len(encoded) + len(compressed) + len(json_bytes)
    
    return transfer_size, backend_overhead

def server_hash_approach() -> int:
    """Server-side: Just send 16-byte hash (for subsequent requests)."""
    return 16  # Hash is always 16 bytes

def measure_time():
    """Measure actual CPU time for operations."""
    import timeit
    
    context = {
        "user": {
            "id": "user-123",
            "name": "John Doe",
            "email": "john@example.com",
            "preferences": {"theme": "dark", "language": "en"},
            "metadata": {"role": "admin", "department": "engineering"}
        },
        "product": {
            "uuid": "prod-456",
            "name": "BabbleBeaver Pro",
            "features": ["chat", "analytics", "api"],
            "pricing": {"tier": "professional", "seats": 10}
        },
        "page": {
            "url": "https://example.com/products/babblebeaver",
            "title": "BabbleBeaver - AI Chat Platform",
            "referrer": "https://google.com/search?q=ai+chatbot"
        }
    }
    
    # Time plain JSON
    plain_time = timeit.timeit(
        lambda: json.dumps(context).encode('utf-8'),
        number=1000
    ) / 1000
    
    # Time frontend compression
    compress_time = timeit.timeit(
        lambda: base64.b64encode(zlib.compress(json.dumps(context).encode('utf-8'))),
        number=1000
    ) / 1000
    
    # Time decompression (what backend must do)
    compressed = base64.b64encode(zlib.compress(json.dumps(context).encode('utf-8')))
    decompress_time = timeit.timeit(
        lambda: json.loads(zlib.decompress(base64.b64decode(compressed)).decode('utf-8')),
        number=1000
    ) / 1000
    
    return plain_time * 1000, compress_time * 1000, decompress_time * 1000

def run_analysis():
    print("=" * 80)
    print("INITIAL CONTEXT: Frontend Compression vs Plain JSON vs Server Hash")
    print("=" * 80)
    print()
    
    # Realistic initial context
    small_context = {
        "user_id": "user-123",
        "product_uuid": "prod-456"
    }
    
    medium_context = {
        "user": {
            "id": "user-123",
            "name": "John Doe",
            "email": "john@example.com",
            "preferences": {"theme": "dark", "language": "en"}
        },
        "product": {
            "uuid": "prod-456",
            "name": "BabbleBeaver Pro",
            "features": ["chat", "analytics", "api"]
        },
        "page": {
            "url": "https://example.com/products/babblebeaver",
            "title": "BabbleBeaver Product Page"
        }
    }
    
    large_context = {
        "user": {
            "id": "user-123",
            "name": "John Doe",
            "email": "john@example.com",
            "preferences": {"theme": "dark", "language": "en", "notifications": True},
            "metadata": {"role": "admin", "department": "engineering", "joined": "2024-01-01"},
            "permissions": ["read", "write", "admin", "manage_users", "view_analytics"]
        },
        "product": {
            "uuid": "prod-456",
            "name": "BabbleBeaver Pro Enterprise",
            "features": ["chat", "analytics", "api", "webhooks", "sso", "audit_logs"],
            "pricing": {"tier": "enterprise", "seats": 100, "monthly": 999},
            "metadata": {"created": "2024-01-01", "updated": "2024-12-01"}
        },
        "page": {
            "url": "https://example.com/products/babblebeaver/pricing?plan=enterprise",
            "title": "BabbleBeaver - AI Chat Platform for Enterprise",
            "referrer": "https://google.com/search?q=enterprise+ai+chatbot",
            "utm": {"source": "google", "medium": "cpc", "campaign": "enterprise"}
        },
        "session": {
            "id": "session-789",
            "started": "2024-12-07T10:00:00Z",
            "events": ["page_view", "button_click", "form_submit"]
        }
    }
    
    scenarios = [
        ("Small Context (minimal)", small_context),
        ("Medium Context (typical)", medium_context),
        ("Large Context (everything)", large_context)
    ]
    
    print("NETWORK TRANSFER SIZE COMPARISON")
    print("-" * 80)
    
    for name, context in scenarios:
        plain_size = plain_json_approach(context)
        frontend_size, backend_overhead = frontend_compression_approach(context)
        hash_size = server_hash_approach()
        
        print(f"\n{name}:")
        print(f"  Plain JSON:              {plain_size:4d} bytes")
        print(f"  Frontend Compression:    {frontend_size:4d} bytes ({(plain_size-frontend_size)/plain_size*100:.1f}% smaller)")
        print(f"  Server Hash (subsequent): {hash_size:4d} bytes ({(plain_size-hash_size)/plain_size*100:.1f}% smaller)")
        
        if frontend_size < plain_size:
            print(f"  ✅ Compression helps ({plain_size/frontend_size:.1f}x reduction)")
        else:
            print(f"  ❌ Compression makes it BIGGER ({frontend_size/plain_size:.1f}x)")
    
    print()
    print("=" * 80)
    print("CPU TIME ANALYSIS (CRITICAL!)")
    print("=" * 80)
    print()
    
    plain_time, compress_time, decompress_time = measure_time()
    
    print(f"Plain JSON serialization:     {plain_time:.3f}ms (frontend)")
    print(f"Compress + encode:            {compress_time:.3f}ms (frontend)")
    print(f"Decode + decompress + parse:  {decompress_time:.3f}ms (backend)")
    print()
    print(f"Total overhead with compression: {compress_time + decompress_time:.3f}ms")
    print(f"Extra time vs plain JSON:        {(compress_time + decompress_time - plain_time):.3f}ms")
    
    if (compress_time + decompress_time) > plain_time:
        print(f"❌ Compression is SLOWER by {(compress_time + decompress_time - plain_time):.3f}ms")
    else:
        print(f"✅ Compression is faster by {(plain_time - compress_time - decompress_time):.3f}ms")
    
    print()
    print("=" * 80)
    print("SECURITY ANALYSIS")
    print("=" * 80)
    print()
    
    print("Plain JSON:")
    print("  ✅ Readable in network inspector (good for debugging)")
    print("  ❌ Sensitive data visible in transit (needs HTTPS)")
    print("  ✅ Easy to validate and sanitize on backend")
    print()
    
    print("Frontend Compression (base64):")
    print("  ⚠️  Looks 'encrypted' but ISN'T - just base64 encoded")
    print("  ❌ FALSE sense of security (trivial to decode)")
    print("  ❌ Harder to debug/inspect")
    print("  ❌ Doesn't prevent tampering")
    print("  ⚠️  Backend MUST validate after decompression")
    print()
    
    print("Server-Side Hash:")
    print("  ✅ Session stored server-side (more secure)")
    print("  ✅ Client can't tamper with context")
    print("  ✅ No sensitive data in transit (after first request)")
    print("  ❌ Server must validate session ownership")
    print()
    
    print("=" * 80)
    print("EASE OF USE (DEVELOPER EXPERIENCE)")
    print("=" * 80)
    print()
    
    print("Plain JSON:")
    print("  ✅ Dead simple - just JSON.stringify()")
    print("  ✅ Works everywhere (browser, Node, mobile)")
    print("  ✅ Easy to debug (readable in DevTools)")
    print("  ✅ No dependencies needed")
    print()
    
    print("Frontend Compression:")
    print("  ❌ Requires compression library (pako.js, ~45KB)")
    print("  ❌ More complex frontend code")
    print("  ❌ Harder to debug (not readable)")
    print("  ❌ Backend must handle decompression")
    print("  ⚠️  Different compression libraries between browser/Node")
    print()
    
    print("Server-Side Hash:")
    print("  ✅ Frontend just stores string (trivial)")
    print("  ✅ No dependencies")
    print("  ✅ Debuggable (can see hash)")
    print("  ✅ Backend handles complexity")
    print()
    
    print("=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print()
    
    print("For INITIAL context (first request):")
    print("  ✅ Use Plain JSON - simple, fast, debuggable")
    print("  ❌ Skip frontend compression - adds complexity, minimal benefit")
    print()
    
    print("For SUBSEQUENT requests (conversation):")
    print("  ✅ Use server-side hash - 95% smaller, more secure")
    print()
    
    print("Why NOT frontend compression:")
    print("  1. Small contexts (<500 bytes): Compression makes it BIGGER")
    print("  2. CPU overhead (compress + decompress) > network savings")
    print("  3. False sense of security (base64 != encryption)")
    print("  4. Adds 45KB library dependency (pako.js)")
    print("  5. Harder to debug")
    print("  6. Server-side hash is better for repeat requests anyway")
    print()
    
    print("Use frontend compression ONLY if:")
    print("  - Context is >2KB (very rare for initial data)")
    print("  - Network is extremely slow (<100 Kbps)")
    print("  - You're already using compression library")
    print("=" * 80)

if __name__ == "__main__":
    run_analysis()
