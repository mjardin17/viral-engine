# PROJECT_IDENTITY — Auto Poster Bot
**Empire Inspector Score:** 45% — KEEP (incomplete)
**Location:** Separate project (not locally accessible)
**Stack:** Node.js (Vanilla), Puppeteer

---

## What This Project Does
Headless cron post publisher with bypass bot detection. Uses Puppeteer (headless Chrome) to automate social media posting when platform APIs are unavailable or restricted. Runs on a cron schedule.

## What Problems It Solves
- Posts content to platforms that don't have open APIs (or where API approval is pending)
- Bypasses bot-detection mechanisms on social platforms
- Automates scheduled posting without manual intervention

## What APIs It Exposes
Unknown — likely a job queue interface or CLI trigger
- Receives publish jobs (post content + target platform + schedule)
- Returns post status / confirmation

## What Files Are Important
(Not locally accessible — separate Node.js project)
- Puppeteer browser automation scripts
- Cron scheduler
- Platform-specific posting scripts (one per platform)

## What AI Models It Uses
- None directly — it's a browser automation tool, not an AI model
- Receives pre-generated content from CrossPost/Content Ingress

## What Other Projects It Can Connect To
- **CrossPost / Content Ingress** — receives publish jobs as queue items
- **Empire OS Automation Center** — cron scheduling
- **Video Bot Pipeline** — receives finished MP4 paths for upload

## What It Should NEVER Duplicate
- Content generation (CrossPost / StoryForge / Video Bot Pipeline)
- Video rendering (Video Bot Pipeline)
- Platform API publishing where an official API exists (YouTube Data API v3 is free and works)

## Current Completion
**45%** per Empire Inspector — significantly incomplete

## Missing Features
- Most posting scripts likely unfinished or broken
- Bot-detection bypass may be fragile (platform anti-bot measures evolve)
- No status reporting back to Empire OS
- May conflict with official YouTube Data API v3 approach (avoid duplication)
- Recommend: use official APIs where available; use Auto Poster Bot only as fallback for API-restricted platforms
