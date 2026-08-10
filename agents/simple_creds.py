#!/usr/bin/env python3
"""Simple credential collector - just text prompts."""

from pathlib import Path

# Platform types: "browser" = username+password, "api" = token only
PLATFORMS = [
    ("whatnot", "Whatnot", "browser"),
    ("mercari", "Mercari", "browser"),
    ("facebook", "Facebook Marketplace", "browser"),
    ("etsy", "Etsy", "api"),
    ("pinterest", "Pinterest", "api"),
]

print("\n" + "="*70)
print("CREDENTIAL SETUP")
print("="*70)
print("\nPress Enter to skip any platform.\n")

creds = {}

# Load existing .env if it exists
env_file = Path(".env")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                creds[k.strip()] = v.strip()

for platform, display_name, ptype in PLATFORMS:
    print(f"▶ {display_name}")

    if ptype == "api":
        # API platforms - just ask for token
        token = input(f"  API Token/Key: ").strip()
        if not token:
            print(f"  (skipped)\n")
            continue

        if platform == "etsy":
            creds["ETSY_TOKEN"] = token
        elif platform == "pinterest":
            creds["PINTEREST_TOKEN"] = token

        print(f"  ✓ Saved\n")

    else:  # browser
        # Browser platforms - ask for username and password
        username = input(f"  Username/Email: ").strip()
        if not username:
            print(f"  (skipped)\n")
            continue

        password = input(f"  Password: ").strip()
        if not password:
            print(f"  (skipped)\n")
            continue

        if platform == "whatnot":
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
