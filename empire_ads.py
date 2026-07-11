"""
empire_ads.py — Empire OS Self-Advertising Automation
Generates and schedules promotional content for all 11 services across platforms.
Usage: python empire_ads.py --website https://jardins-outpost.pages.dev
"""
import os
import json
import argparse
import random
from datetime import datetime, timedelta
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

# --- CONFIG ---
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "echoes-council", ".env"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SERVICES = [
    {"name": "AI Video Production",          "price": "$500–$2,500/episode",   "hook": "done-for-you YouTube videos, script to finished MP4"},
    {"name": "Social Media Automation",       "price": "$500–$1,500/month",     "hook": "daily posts across Instagram, TikTok, Facebook, X — hands-free"},
    {"name": "SEO Content Machine",           "price": "$300–$800/month",       "hook": "weekly blog posts that rank on Google and drive inbound leads"},
    {"name": "Email Marketing Sequences",     "price": "$750–$2,500/sequence",  "hook": "welcome flows and nurture campaigns that convert while you sleep"},
    {"name": "Website Design",                "price": "$1,500–$5,000",         "hook": "professional mobile-ready websites built and deployed in days"},
    {"name": "AI Chatbots",                   "price": "$1,000–$3,000",         "hook": "24/7 AI sales rep trained on your business, embedded on your site"},
    {"name": "YouTube Channel Management",    "price": "$2,000–$6,000/month",   "hook": "full channel operation — scripted, produced, upload-ready weekly"},
    {"name": "Ad Copy Packages",              "price": "$500–$1,500/campaign",  "hook": "10–20 ad variations for Facebook, Google, TikTok ready to run"},
    {"name": "Custom AI Pipeline",            "price": "$5,000–$25,000",        "hook": "your own Empire OS — a custom AI system that runs your business"},
    {"name": "Reseller & Inventory Apps",     "price": "$3,000–$10,000",        "hook": "custom cross-listing and inventory management tools for resellers"},
    {"name": "AI Brand Identity Package",     "price": "$1,500–$4,000",         "hook": "brand voice, messaging pillars, taglines, and 30-day content strategy"},
]

PLATFORMS = ["instagram", "tiktok", "facebook", "twitter"]

PLATFORM_STYLES = {
    "instagram": "visual and casual, use emojis naturally, conversational tone, feel aspirational",
    "tiktok":    "punchy and fast, hook in first 3 words, high energy, very short sentences, use trending language",
    "facebook":  "detailed and professional, explain the value clearly, business owner audience, trust-building",
    "twitter":   "bold and short, under 240 characters total, direct value statement, minimal fluff",
}

POST_TIMES = {
    "instagram": ["09:00", "18:00"],
    "tiktok":    ["12:00", "20:00"],
    "facebook":  ["10:00", "15:00"],
    "twitter":   ["08:00", "17:00"],
}


def generate_service_ad(service_name: str, platform: str, website_url: str) -> dict:
    """Generate ad copy for a service on a specific platform using Gemini."""
    service = next((s for s in SERVICES if s["name"] == service_name), None)
    if not service:
        return {"error": f"Service '{service_name}' not found"}

    style = PLATFORM_STYLES.get(platform, "professional")

    prompt = f"""
You are a social media copywriter for Empire OS, an AI automation agency.

Write a {platform} ad for this service:
Service: {service['name']}
Price: {service['price']}
Core value: {service['hook']}
Platform style: {style}

Return ONLY valid JSON:
{{
  "hook": "One punchy opening sentence — platform-specific style",
  "body": "2-3 sentences explaining the value and outcome for the business owner",
  "cta": "Call to action ending with: {website_url}",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3", "hashtag4", "hashtag5"]
}}

Rules:
- hook must grab attention immediately
- body focuses on OUTCOME not features
- cta is action-oriented (e.g. "DM us", "Book a call", "See what we build")
- hashtags relevant to the service and platform
- For twitter: entire post (hook + body + cta) must be under 240 characters
"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        data = json.loads(response.text)
        data["service"]  = service_name
        data["platform"] = platform
        return data
    except Exception as e:
        return {
            "error": str(e),
            "service": service_name,
            "platform": platform,
            "hook": f"Stop doing everything manually. {service['hook'].capitalize()}.",
            "body": f"Empire OS builds and runs your {service_name.lower()} on autopilot. {service['price']}.",
            "cta": f"See what we build → {website_url}",
            "hashtags": ["#AIautomation", "#EmpireOS", "#BusinessGrowth", "#AItools", "#Automation"],
        }


def generate_weekly_schedule(website_url: str) -> list:
    """
    Rotate all 11 services across 7 days, 2 posts/day per platform.
    Returns list of scheduled posts with service, platform, copy, and post_time.
    """
    schedule = []
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    service_index = 0

    for day_offset in range(7):
        post_date = start_date + timedelta(days=day_offset)

        for platform in PLATFORMS:
            times = POST_TIMES[platform]
            for post_slot, time_str in enumerate(times):
                service = SERVICES[service_index % len(SERVICES)]
                hour, minute = map(int, time_str.split(":"))
                post_datetime = post_date.replace(hour=hour, minute=minute)

                print(f"  Generating: {service['name']} → {platform} @ {post_datetime.strftime('%a %b %d %H:%M')}")
                ad = generate_service_ad(service["name"], platform, website_url)

                schedule.append({
                    "id":           f"{post_datetime.strftime('%Y%m%d')}_{platform}_{service_index % len(SERVICES):02d}",
                    "service":      service["name"],
                    "platform":     platform,
                    "post_time":    post_datetime.isoformat(),
                    "day":          post_datetime.strftime("%A"),
                    "hook":         ad.get("hook", ""),
                    "body":         ad.get("body", ""),
                    "cta":          ad.get("cta", ""),
                    "hashtags":     ad.get("hashtags", []),
                    "full_post":    f"{ad.get('hook','')} {ad.get('body','')} {ad.get('cta','')} {' '.join(ad.get('hashtags',[]))}",
                    "status":       "scheduled",
                    "website_url":  website_url,
                })
                service_index += 1

    return schedule


def save_schedule(schedule: list, output_file: str = "ads_schedule.json") -> str:
    """Save the weekly schedule to JSON for Zernio to consume."""
    output_path = os.path.join(os.path.dirname(__file__), output_file)
    payload = {
        "generated_at":  datetime.now().isoformat(),
        "total_posts":   len(schedule),
        "platforms":     PLATFORMS,
        "services_count": len(SERVICES),
        "posts":         schedule,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return output_path


# --- CLI ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Empire OS Self-Advertising Engine")
    parser.add_argument("--website",  default="https://jardins-outpost.pages.dev", help="Website URL for CTAs")
    parser.add_argument("--output",   default="ads_schedule.json", help="Output JSON filename")
    parser.add_argument("--service",  default=None, help="Test a single service ad (optional)")
    parser.add_argument("--platform", default="instagram", help="Platform for single service test")
    parser.add_argument("--test",     action="store_true", help="Test Gemini connection only")
    args = parser.parse_args()

    if args.test:
        print("Testing Gemini API...")
        result = generate_service_ad("AI Video Production", "instagram", args.website)
        if "error" in result:
            print(f"✗ Failed: {result['error']}")
        else:
            print("✓ Gemini connected. Sample ad:")
            print(json.dumps(result, indent=2))

    elif args.service:
        print(f"Generating single ad: {args.service} → {args.platform}")
        result = generate_service_ad(args.service, args.platform, args.website)
        print(json.dumps(result, indent=2))

    else:
        print(f"Empire OS — Generating weekly ad schedule")
        print(f"Website: {args.website}")
        print(f"Services: {len(SERVICES)} | Platforms: {len(PLATFORMS)} | Days: 7")
        print(f"Total posts: {len(SERVICES) * len(PLATFORMS) * 2} estimated\n")

        schedule = generate_weekly_schedule(args.website)
        output_path = save_schedule(schedule, args.output)

        print(f"\n✓ Schedule complete — {len(schedule)} posts generated")
        print(f"  Saved to: {output_path}")
        print(f"\nNext step: Load ads_schedule.json into Zernio to start posting.")
