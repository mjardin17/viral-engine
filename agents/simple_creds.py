#!/usr/bin/env python3
"""Simple credential collector - just text prompts."""

from pathlib import Path

PLATFORMS = [
    ("whatnot", "Whatnot"),
    ("mercari", "Mercari"),
    ("facebook", "Facebook Marketplace"),
    ("etsy", "Etsy"),
]

print("\n" + "="*70)
print("CREDENTIAL SETUP - SIMPLE")
print("="*70)
print("\nJust answer the prompts. Press Enter to skip a platform.\n")

creds = {}

# Load existing .env if it exists
env_file = Path(".env")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                creds[k.strip()] = v.strip()

for platform, display_name in PLATFORMS:
    print(f"▶ {display_name}")

    username = input(f"  Username/Email: ").strip()
    if not username:
        print(f"  (skipped)\n")
        continue

    password = input(f"  Password: ").strip()
    if not password:
        print(f"  (skipped)\n")
        continue

    # Store credentials
    if platform == "etsy":
        creds["ETSY_TOKEN"] = username
    elif platform == "whatnot":
        creds["WHATNOT_USERNAME"] = username
        creds["WHATNOT_PASSWORD"] = password
    elif platform == "mercari":
        creds["MERCARI_EMAIL"] = username
        creds["MERCARI_PASSWORD"] = password
    elif platform == "facebook":
        creds["FACEBOOK_EMAIL"] = username
        creds["FACEBOOK_PASSWORD"] = password

    print(f"  ✓ Saved\n")

# Save to .env
if creds:
    with open(env_file, "w") as f:
        f.write("# Credentials\n")
        for k, v in sorted(creds.items()):
            f.write(f"{k}={v}\n")

    print("="*70)
    print(f"✓ Saved to .env")
    print(f"✓ {len(creds)} credentials saved")
    print("="*70 + "\n")
else:
    print("No credentials added\n")
