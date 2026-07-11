# Empire OS — Security Report
**Date: 2026-07-05 | Auditor: Claude | Priority: IMMEDIATE ACTION REQUIRED**

---

## 🔴 CRITICAL-1: API Keys Committed to Git

### What happened
`apps/empire-os-server/.env` contains live API keys and is **tracked by git**.

```
git ls-files apps/empire-os-server/.env
→ apps/empire-os-server/.env   ← TRACKED (confirmed 2026-07-05)
```

The file contains live credentials for Anthropic, Google, and commented-but-visible keys for OpenAI, Pexels, and ElevenLabs. Because this file is in git history, the keys are exposed to anyone with repo access — including the GitHub remote (`mjardin17/viral-engine`) if it was ever pushed with this file tracked.

### Keys to rotate immediately (in this order)
1. **Anthropic** → https://console.anthropic.com/settings/keys → Delete the exposed key, create new one
2. **Google AI** → https://aistudio.google.com/app/apikey → Delete the exposed key, create new one
3. **OpenAI** (even though commented) → https://platform.openai.com/api-keys → Rotate to be safe
4. **Pexels** → https://www.pexels.com/api/ → Rotate
5. **ElevenLabs** → https://elevenlabs.io/app/settings/api-keys → Rotate

### Remediation steps (Josh must rotate keys first, THEN run these)

**Step 1 — Remove from git tracking (run in repo root):**
```bat
cd C:\Users\jjard\claude\video-bot-pipeline
git rm --cached empire-os-patch/apps/empire-os-server/.env
```

**Step 2 — Add to .gitignore:**
The root `.gitignore` already has `.env` listed, BUT the empire-os-patch subdirectory has no `.gitignore`. Add one:
```
echo .env > empire-os-patch\apps\empire-os-server\.gitignore
echo .env >> empire-os-patch\.gitignore
```

**Step 3 — Commit the removal:**
```bat
git add empire-os-patch/apps/empire-os-server/.gitignore empire-os-patch/.gitignore
git commit -m "[CLAUDE] security: remove .env from git tracking, add .gitignore"
git push origin main
```

**Step 4 — Purge from git history (optional but recommended):**
If the repo has been pushed to GitHub with the keys tracked, the history contains them. To fully purge:
```bat
git filter-repo --path empire-os-patch/apps/empire-os-server/.env --invert-paths
git push origin main --force
```
⚠️ `git filter-repo` requires install: `pip install git-filter-repo`. Force-push rewrites history — coordinate with any collaborators first.

**Step 5 — Verify:**
```bat
git log --all --full-history -- empire-os-patch/apps/empire-os-server/.env
```
After filter-repo this should return nothing.

---

## 🔴 CRITICAL-2: No .gitignore in empire-os-patch/

The monorepo subdirectory `empire-os-patch/` has no `.gitignore`. The root `.gitignore` protects the top-level repo but subdirectory `.env` files are not covered by it by default.

**Fix:** Already covered in CRITICAL-1 remediation (Step 2 above).

Also verify these are NOT tracked:
```bat
git ls-files empire-os-patch/ | grep -E "\.env|\.key|\.token"
```

---

## 🔴 HIGH-1: EMPIRE_API_KEY Not Set — Auth is Completely Disabled

The Empire OS server's authentication is entirely optional. When `EMPIRE_API_KEY` is blank (current state), every endpoint — including `/executive/`, `/job-scheduler/jobs/:id/run`, `/notification/emit`, `/metrics-engine/reset` — is accessible by anyone who can reach port 3001.

```typescript
// server.ts line ~65
const API_KEY = process.env.EMPIRE_API_KEY  // undefined = auth disabled (dev mode)
```

**Fix:** Set a strong key in `.env`:
```
EMPIRE_API_KEY=<generate with: node -e "console.log(require('crypto').randomBytes(32).toString('hex'))">
```
Then include `X-Empire-Api-Key: <key>` header in all API calls from the dashboard and CrossPost.

---

## 🟡 MEDIUM-1: CORS Wildcard

```typescript
// server.ts
res.setHeader('Access-Control-Allow-Origin', '*')
```

Any origin can call the Empire OS API. While acceptable in local dev (no public internet exposure), this should be restricted before any cloud deployment.

**Fix for production:**
```typescript
const ALLOWED_ORIGINS = new Set([
  'http://localhost:3000',  // CrossPost
  'http://localhost:3001',  // Empire OS itself
  process.env.DASHBOARD_URL ?? '',
])

res.setHeader('Access-Control-Allow-Origin',
  ALLOWED_ORIGINS.has(req.headers.origin ?? '') ? req.headers.origin! : '')
```

---

## 🟡 MEDIUM-2: No Rate Limiting

The Empire OS HTTP server has no rate limiting. A local process that issues rapid requests to `/executive/briefing/generate` (which calls AI) or `/installer/` (which installs software) could cause runaway AI spend or system changes.

**Fix:** Add a simple in-memory rate limiter per IP to server.ts, or use `express-rate-limit` if CrossPost ever wraps this via Express.

---

## 🟡 MEDIUM-3: CrossPost GitHub OAuth Token Exposure Risk

CrossPost (`server.ts` ~line 2182–2340) implements GitHub OAuth. The exchange of the auth code for a token happens server-side — correct. However:
- GitHub client ID/secret are read from `process.env.GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`
- These must be in CrossPost's own `.env` — verify CrossPost's `.env` is not tracked:
```bat
git ls-files empire-os-patch/apps/crosspost-enterprise/.env
```
Should return nothing.

---

## 🟡 MEDIUM-4: adm-zip in CrossPost

`adm-zip ^0.5.18` is used in CrossPost for ZIP generation. This library has had path traversal CVEs in past versions. Verify the installed version is patched:
```bat
cd empire-os-patch/apps/crosspost-enterprise && npm list adm-zip
```
Ensure it's `0.5.10` or later (CVE-2023-0842 was fixed in 0.5.10).

---

## 🟢 LOW-1: empireEvents Global Pattern (CrossPost)

```typescript
if (typeof empireEvents !== 'undefined') {
  empireEvents.push(gitEvent);
}
```

This pattern is used 5+ times in crosspost/server.ts. It means empire event emission is silently skipped if the variable is undefined. No error, no log. Replace with a proper event emitter or guaranteed-defined module-level array.

---

## 🟢 LOW-2: Job Scheduler Hardcodes localhost:3001

Built-in jobs use hardcoded `http://localhost:3001/watchdog/backup` etc. If the server moves ports or is deployed remotely, jobs silently fail.

**Fix:** Replace with `process.env.EMPIRE_BASE_URL ?? 'http://localhost:3001'`.

---

## 🟢 LOW-3: logger.module.ts Query Param Bug

```typescript
private qp(req: GatewayRequest, key: string): string | undefined {
  const headers = req.headers as Record<string, string>
  return headers[`x-qp-${key}`] ?? undefined
}
```

Query params (`?limit=100&level=ERROR`) are extracted from custom headers (`x-qp-limit`, `x-qp-level`) rather than the URL. This means all GET search/filter params for the logger are silently ignored unless the caller sends custom headers. The module gateway must be injecting these, but if not configured, all filter routes return unfiltered results silently.

**Fix:** Parse the query string from `req.path` directly inside `qp()` or ensure the module gateway properly injects query params as `x-qp-*` headers.

---

## Summary

| # | Severity | Issue | Action |
|---|----------|-------|--------|
| 1 | 🔴 CRITICAL | .env with live keys committed to git | Rotate keys → git rm --cached → add .gitignore |
| 2 | 🔴 CRITICAL | No .gitignore in empire-os-patch/ | Add .gitignore |
| 3 | 🔴 HIGH | Auth disabled (EMPIRE_API_KEY blank) | Set strong key in .env |
| 4 | 🟡 MEDIUM | CORS wildcard | Lock down for production |
| 5 | 🟡 MEDIUM | No rate limiting | Add in-memory limiter |
| 6 | 🟡 MEDIUM | CrossPost GitHub OAuth credentials | Verify not tracked |
| 7 | 🟡 MEDIUM | adm-zip version | Verify ≥0.5.10 |
| 8 | 🟢 LOW | empireEvents global guards | Use guaranteed-defined module variable |
| 9 | 🟢 LOW | Hardcoded localhost:3001 in job scheduler | Use env var |
| 10 | 🟢 LOW | logger qp() query param parsing | Fix to parse from URL |

**⚠️ DO NOT PUSH ANY CODE until keys are rotated and .env is removed from tracking.**
