#!/usr/bin/env python3
"""Test credential collector."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.credential_collector_agent import CredentialCollector

collector = CredentialCollector()

print("="*70)
print("CREDENTIAL COLLECTOR AGENT TEST")
print("="*70)

# Show all platforms
print(f"\n✓ Loaded guides for {len(collector.PLATFORM_GUIDES)} platforms:\n")

for platform in sorted(collector.PLATFORM_GUIDES.keys()):
    guide = collector.PLATFORM_GUIDES[platform]
    env_var = guide.get("env_var")
    is_configured = env_var in collector.credentials
    status = "✓ CONFIGURED" if is_configured else "⊘ NOT SET"
    print(f"  {platform:20s} → {guide['name']:25s} [{status}]")

print(f"\n{'='*70}")
print("Ready for credential collection")
print("Run: GET_CREDENTIALS.bat")
print("="*70)
