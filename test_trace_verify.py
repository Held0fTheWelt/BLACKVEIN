#!/usr/bin/env python3
"""Verify Langfuse tracing is working by sending a test trace."""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 70)
print("Langfuse Tracing Verification Test")
print("=" * 70)

# Check credentials
public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
secret_key = os.getenv("LANGFUSE_SECRET_KEY")
base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

print(f"\n[CONFIG]")
print(f"  LANGFUSE_BASE_URL: {base_url}")
print(f"  Public Key: {public_key[:20] if public_key else 'MISSING'}...")
print(f"  Secret Key: {secret_key[:20] if secret_key else 'MISSING'}...")

if not public_key or not secret_key:
    print("\n[ERROR] Missing Langfuse credentials")
    sys.exit(1)

print("\n[INITIALIZING] Langfuse SDK with correct v4.x parameters...")
try:
    from langfuse import Langfuse, observe

    # Initialize with correct parameter names (base_url, not host/baseUrl)
    client = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        base_url=base_url,
    )
    print("[✓] Langfuse client initialized successfully")
except Exception as e:
    print(f"[ERROR] Failed to initialize Langfuse: {e}")
    sys.exit(1)

print("\n[SENDING] Test trace to Langfuse...")

# Test 1: Using @observe decorator
@observe()
def test_operation_with_decorator():
    """Simple operation to trace."""
    time.sleep(0.5)
    return {"status": "success", "timestamp": time.time()}

# Test 2: Using observation API (like backend adapter does)
def test_operation_with_observation():
    """Test using observation API."""
    span = client.start_observation(
        as_type="span",
        name="test.operation.direct",
        metadata={
            "test_type": "direct_observation",
            "timestamp": time.time(),
        }
    )

    time.sleep(0.5)
    span.end()

try:
    # Send trace 1: using decorator
    print("  1. Tracing with @observe decorator...")
    result1 = test_operation_with_decorator()
    print(f"     → Result: {result1}")

    # Send trace 2: using observation API
    print("  2. Tracing with observation API...")
    test_operation_with_observation()
    print(f"     → Done")

    # Flush to ensure all traces are sent
    print("\n[FLUSHING] Sending all traces to Langfuse...")
    client.flush()

    print("[✓] Flush completed\n")

except Exception as e:
    print(f"[ERROR] Failed to send trace: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Wait for traces to transmit
print("[WAITING] Allowing 3 seconds for traces to transmit...")
time.sleep(3)

print("\n" + "=" * 70)
print("SUCCESS - Traces sent to Langfuse!")
print("=" * 70)
print("\nNext steps:")
print(f"  1. Open Langfuse dashboard: {base_url}")
print("  2. Look for 'test_operation_with_decorator' trace")
print("  3. Look for 'test.operation.direct' span")
print("  4. Verify traces contain the test data\n")
