#!/usr/bin/env python3
"""
test_ollama_fallback.py — Verify Ollama fallback works in ClaudeAdapter.

Run this after:
1. Ollama is running (ollama serve)
2. qwen2.5-coder:7b model is pulled (ollama pull qwen2.5-coder:7b)
3. ANTHROPIC_API_KEY is NOT set in .env (to force fallback)
"""

import sys
from pathlib import Path

# Add repo to path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))

from ai_router.adapters.claude_adapter import ClaudeAdapter


def test_ollama_fallback():
    """Test that Ollama fallback works when Claude key is missing."""
    adapter = ClaudeAdapter()

    # Verify Claude is NOT connected (force fallback test)
    if adapter.is_connected():
        print("❌ ANTHROPIC_API_KEY is set. Remove it from .env to test fallback.")
        return False

    print("✓ Claude key is not set (will use Ollama fallback)")

    # Simple test prompt
    payload = {
        "task_type": "WRITING",
        "prompt": "Write a single short sentence about Ollama.",
        "system": "You are a helpful assistant.",
        "max_tokens": 100,
    }

    print("\n[Test 1] Ollama fallback with simple prompt...")
    result = adapter.execute(payload)

    if not result.success:
        print(f"❌ Ollama fallback failed: {result.error}")
        print("\nTroubleshooting:")
        print("  1. Is Ollama running? Run: ollama serve")
        print("  2. Is qwen2.5-coder:7b pulled? Run: ollama pull qwen2.5-coder:7b")
        print("  3. Is http://localhost:11434 accessible?")
        return False

    print(f"✓ Ollama fallback succeeded!")
    print(f"  Provider: {result.meta.get('provider')}")
    print(f"  Model: {result.meta.get('model')}")
    print(f"  Latency: {result.latency_ms}ms")
    print(f"  Output (first 100 chars): {result.output[:100]}...")

    # Test 2: Verify Claude fails gracefully if key is set but invalid
    print("\n[Test 2] Invalid Claude key + valid Ollama fallback...")
    import os
    os.environ["ANTHROPIC_API_KEY"] = "invalid-key-for-testing"

    result2 = adapter.execute(payload)
    if result2.success and result2.meta.get("provider") == "ollama":
        print(f"✓ Correctly fell back to Ollama when Claude key was invalid")
        return True
    else:
        print(f"❌ Should have fallen back to Ollama on invalid Claude key")
        print(f"   Result: {result2.error}")
        return False


if __name__ == "__main__":
    print("Testing Ollama fallback in ClaudeAdapter...\n")
    success = test_ollama_fallback()
    sys.exit(0 if success else 1)
