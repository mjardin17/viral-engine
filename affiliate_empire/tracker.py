"""
affiliate_empire/tracker.py — Empire OS Affiliate Program Tracker
Tracks every affiliate program, signup status, IDs, and commission rates.

Usage:
    python affiliate_empire/tracker.py --status
    python affiliate_empire/tracker.py --apply amazon-associates
    python affiliate_empire/tracker.py --mark-joined amazon-associates --id "empireos-20"
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT         = Path(__file__).parent.parent
STATUS_FILE  = Path(__file__).parent / "AFFILIATE_STATUS.json"
ENV_FILE     = ROOT / ".env"

# ── Program definitions ───────────────────────────────────────────────────────

PROGRAMS: dict[str, dict] = {
    "amazon-associates": {
        "name":        "Amazon Associates",
        "apply_url":   "https://affiliate-program.amazon.com/",
        "commission":  "4–10% per sale",
        "payout":      "60 days after month end",
        "best_for":    "Books, merch, product links in video descriptions",
        "approval":    "auto (need 3 sales in 180 days)",
        "env_key":     "AMAZON_ASSOCIATES_TAG",
        "link_format": "https://www.amazon.com/dp/{ASIN}?tag={ID}",
        "notes":       "Apply with your website URL. Tag looks like: empireos-20",
    },
    "audible": {
        "name":        "Audible Affiliate (Amazon)",
        "apply_url":   "https://www.amazon.com/gp/audible/referral-program/",
        "commission":  "$5 per free trial, $15 per paid signup",
        "payout":      "Monthly",
        "best_for":    "GG / StoryForge audiobook promotion",
        "approval":    "via Amazon Associates account",
        "env_key":     "AUDIBLE_AFFILIATE_TAG",
        "link_format": "https://www.audible.com/?source_code=AUDFPWS0223189MWT-BK-ACX0-{ID}",
        "notes":       "Enable through your existing Amazon Associates account",
    },
    "nordvpn": {
        "name":        "NordVPN Affiliate",
        "apply_url":   "https://affiliate.nordvpn.com/",
        "commission":  "$40–$100 per signup (40% on plans)",
        "payout":      "Monthly via PayPal/wire",
        "best_for":    "ED (tech) and GG channels — universal audience",
        "approval":    "1–3 business days",
        "env_key":     "NORDVPN_AFFILIATE_ID",
        "link_format": "https://nordvpn.com/?utm_medium=affiliate&utm_term={ID}",
        "notes":       "Highest single-commission affiliate on this list. Apply NOW.",
    },
    "tubebuddy": {
        "name":        "TubeBuddy Affiliate",
        "apply_url":   "https://www.tubebuddy.com/affiliate",
        "commission":  "30–50% recurring monthly",
        "payout":      "Monthly via PayPal",
        "best_for":    "Any YouTube-creator-adjacent content",
        "approval":    "Instant",
        "env_key":     "TUBEBUDDY_AFFILIATE_ID",
        "link_format": "https://www.tubebuddy.com/pricing?a={ID}",
        "notes":       "Recurring commission — every month a customer stays, you earn",
    },
    "vidiq": {
        "name":        "VidIQ Affiliate",
        "apply_url":   "https://vidiq.com/affiliates/",
        "commission":  "25% recurring monthly",
        "payout":      "Monthly via PayPal",
        "best_for":    "YouTube creator audience across all channels",
        "approval":    "Instant",
        "env_key":     "VIDIQ_AFFILIATE_ID",
        "link_format": "https://vidiq.com/?ref={ID}",
        "notes":       "Stack with TubeBuddy — mention both in same video",
    },
    "canva": {
        "name":        "Canva Affiliate",
        "apply_url":   "https://www.canva.com/affiliates/",
        "commission":  "$36 per Pro signup",
        "payout":      "Monthly via Impact.com",
        "best_for":    "All channels — huge audience overlap",
        "approval":    "2–5 days via Impact.com",
        "env_key":     "CANVA_AFFILIATE_ID",
        "link_format": "https://www.canva.com/join/{ID}",
        "notes":       "One of the highest-converting affiliate programs anywhere",
    },
    "skillshare": {
        "name":        "Skillshare Affiliate",
        "apply_url":   "https://www.skillshare.com/affiliates",
        "commission":  "$7 per free trial signup",
        "payout":      "Monthly via Impact.com",
        "best_for":    "ED channel — AI/tech/creative learning audience",
        "approval":    "3–5 days via Impact.com",
        "env_key":     "SKILLSHARE_AFFILIATE_ID",
        "link_format": "https://skillshare.eevideo.net/c/{ID}",
        "notes":       "High volume — even 100 signups/month = $700 passive",
    },
    "elevenlabs": {
        "name":        "ElevenLabs Affiliate",
        "apply_url":   "https://elevenlabs.io/affiliates",
        "commission":  "22% recurring for 12 months",
        "payout":      "Monthly",
        "best_for":    "ED channel — perfect fit, you already use the tool",
        "approval":    "Instant",
        "env_key":     "ELEVENLABS_AFFILIATE_ID",
        "link_format": "https://elevenlabs.io/?via={ID}",
        "notes":       "You use this tool = authentic promotion. Recurring for 1 year.",
    },
    "masterclass": {
        "name":        "MasterClass Affiliate",
        "apply_url":   "https://www.masterclass.com/affiliates",
        "commission":  "25% per sale (~$45 per annual plan)",
        "payout":      "Monthly via Impact.com",
        "best_for":    "GG channel — history/documentary audience loves MasterClass",
        "approval":    "3–7 days",
        "env_key":     "MASTERCLASS_AFFILIATE_ID",
        "link_format": "https://www.masterclass.com/?clickId={ID}",
        "notes":       "Gordon Ramsay, Martin Scorsese, David McCullough — GG audience loves this",
    },
    "patreon": {
        "name":        "Patreon (Creator Page)",
        "apply_url":   "https://www.patreon.com/create",
        "commission":  "100% of pledges minus 5–12% Patreon fee",
        "payout":      "Monthly",
        "best_for":    "GG (early episodes) + IL/LO (character art) + ED (behind the scenes)",
        "approval":    "Instant",
        "env_key":     "PATREON_URL",
        "link_format": "https://www.patreon.com/{ID}",
        "notes":       "Set 3 tiers: $3 Early Access, $5 Behind the Scenes, $10 Name in Credits",
    },
    "acx": {
        "name":        "ACX (Audiobook Creation Exchange — Audible)",
        "apply_url":   "https://www.acx.com/",
        "commission":  "25–40% royalty per audiobook sale",
        "payout":      "Monthly",
        "best_for":    "StoryForge books — narrate with ElevenLabs, upload to Audible",
        "approval":    "Instant (just create account and upload)",
        "env_key":     "ACX_EMAIL",
        "link_format": "https://www.audible.com/pd/{ID}",
        "notes":       "Exclusive = 40% royalty. Non-exclusive = 25% but can sell elsewhere too.",
    },
    "gumroad": {
        "name":        "Gumroad (Digital Products)",
        "apply_url":   "https://gumroad.com/",
        "commission":  "90% of sale price (Gumroad takes 10%)",
        "payout":      "Weekly",
        "best_for":    "Sell prompt packs, Empire OS templates, episode scripts",
        "approval":    "Instant",
        "env_key":     "GUMROAD_URL",
        "link_format": "https://gumroad.com/{ID}",
        "notes":       "Sell: GG prompt pack $9.99, IL character prompts $14.99, Empire OS blueprint $49",
    },
    "impact": {
        "name":        "Impact.com (Affiliate Network)",
        "apply_url":   "https://app.impact.com/signup/publisher/",
        "commission":  "Varies by brand (Canva, Skillshare, etc. all pay via Impact)",
        "payout":      "Monthly",
        "best_for":    "One account unlocks Canva, Skillshare, MasterClass, and 1000+ more",
        "approval":    "1–2 days",
        "env_key":     "IMPACT_ACCOUNT_ID",
        "link_format": "Varies per brand",
        "notes":       "Apply to Impact first — then apply to individual brands inside the platform",
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_status() -> dict:
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    return {}


def save_status(data: dict) -> None:
    STATUS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_env() -> dict:
    env: dict = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def save_env_key(key: str, value: str) -> None:
    env = load_env()
    env[key] = value
    lines = ["# Empire OS credentials", ""]
    for k, v in env.items():
        lines.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def open_url(url: str) -> None:
    try:
        subprocess.Popen(["cmd", "/c", "start", url], shell=False)
    except Exception:
        print(f"    Open: {url}")


# ── Status display ────────────────────────────────────────────────────────────

def print_status() -> None:
    data = load_status()
    env  = load_env()

    print("\n" + "=" * 70)
    print("  EMPIRE OS — Affiliate Empire Status")
    print("=" * 70)

    total = joined = 0
    for key, p in PROGRAMS.items():
        total += 1
        state  = data.get(key, {})
        active = state.get("joined", False)
        aff_id = env.get(p["env_key"], "")

        if active and aff_id:
            joined += 1
            icon   = "✅"
            status = f"ACTIVE — ID: {aff_id[:20]}..."
        elif active:
            icon   = "⏳"
            status = f"Joined — add {p['env_key']} to .env"
        else:
            icon   = "❌"
            status = f"Not applied"

        print(f"\n  {icon}  {p['name']}")
        print(f"       Commission : {p['commission']}")
        print(f"       Best for   : {p['best_for']}")
        print(f"       Status     : {status}")

    print(f"\n{'=' * 70}")
    print(f"  Joined: {joined}/{total} programs")
    est = joined * 150  # rough estimate per program per month at scale
    print(f"  Estimated monthly (at scale): ${est:,}+")
    print("=" * 70 + "\n")


# ── Apply guide ───────────────────────────────────────────────────────────────

def apply_guide(key: str) -> None:
    p = PROGRAMS[key]
    print(f"\n{'=' * 60}")
    print(f"  APPLYING: {p['name']}")
    print(f"  Commission : {p['commission']}")
    print(f"  Approval   : {p['approval']}")
    print(f"  Best for   : {p['best_for']}")
    print(f"  Note       : {p['notes']}")
    print(f"{'=' * 60}")

    print(f"\n  Opening application page...")
    open_url(p["apply_url"])

    input("\n  [Press Enter when you've applied] > ")

    data            = load_status()
    data[key]       = data.get(key, {})
    data[key]["applied"] = True
    save_status(data)

    print(f"\n  ✓ Marked as applied. Once approved, run:")
    print(f"    python affiliate_empire/tracker.py --mark-joined {key} --id YOUR_ID")


def mark_joined(key: str, aff_id: str) -> None:
    p    = PROGRAMS[key]
    data = load_status()
    data[key]         = data.get(key, {})
    data[key]["joined"] = True
    save_status(data)
    save_env_key(p["env_key"], aff_id)
    print(f"\n  ✅ {p['name']} ACTIVE — ID saved to .env as {p['env_key']}")


# ── Run all top programs ──────────────────────────────────────────────────────

def run_all_wizard() -> None:
    data = load_status()
    pending = [k for k, p in PROGRAMS.items() if not data.get(k, {}).get("applied")]

    print(f"\n{'=' * 60}")
    print(f"  AFFILIATE EMPIRE SETUP")
    print(f"  {len(pending)} programs to apply for")
    print(f"  Priority order: highest commissions first")
    print(f"{'=' * 60}\n")

    # Priority order
    priority = [
        "impact",           # unlocks many others
        "nordvpn",          # highest single commission
        "patreon",          # 100% yours
        "amazon-associates",
        "elevenlabs",
        "tubebuddy",
        "vidiq",
        "canva",
        "skillshare",
        "masterclass",
        "audible",
        "acx",
        "gumroad",
    ]

    for key in priority:
        if key not in pending:
            continue
        p = PROGRAMS[key]
        print(f"  → {p['name']}  ({p['commission']})")
        try:
            go = input(f"    Apply now? (Enter=yes, s=skip) > ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        if go != "s":
            apply_guide(key)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Affiliate Empire Tracker")
    ap.add_argument("--status",      action="store_true")
    ap.add_argument("--apply",       metavar="PROGRAM")
    ap.add_argument("--mark-joined", metavar="PROGRAM")
    ap.add_argument("--id",          metavar="AFFILIATE_ID", default="")
    ap.add_argument("--all",         action="store_true", help="Walk through all programs")
    args = ap.parse_args()

    if args.status or not any([args.apply, getattr(args, "mark_joined"), args.all]):
        print_status()

    if args.apply:
        k = args.apply.lower()
        if k not in PROGRAMS:
            print(f"  Unknown: '{k}'. Options: {', '.join(PROGRAMS)}")
        else:
            apply_guide(k)

    if getattr(args, "mark_joined"):
        k = args.mark_joined.lower()
        if k not in PROGRAMS:
            print(f"  Unknown: '{k}'. Options: {', '.join(PROGRAMS)}")
        elif not args.id:
            print(f"  Pass --id YOUR_AFFILIATE_ID")
        else:
            mark_joined(k, args.id)

    if args.all:
        run_all_wizard()
