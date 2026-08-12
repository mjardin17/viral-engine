# Boss Listers Launch Checklist 🚀

**Status:** Infrastructure Complete | Ready for Deployment  
**Last Updated:** 2026-08-12  
**Owner:** Josh Jardin

---

## PRE-LAUNCH VERIFICATION (Do This First)

### ✅ Supabase Project Status
- [ ] **Verify Supabase project exists:** `irslzufsqjveyibkfjtz` ("Boss listers prod")
  - Command: Check console.supabase.com for the project
  - **Current Status:** ✅ Project live (verified 2026-07-28)
- [ ] **Verify all 4 migrations applied:**
  ```
  0001_init_inventory.sql
  0002_schedule_ebay_sync.sql
  0003_commerce_hardening.sql
  0004_channels_and_grants.sql
  ```
  - **Current Status:** ✅ All 4 applied (verified 2026-07-28)
- [ ] **Verify Vault secrets set:**
  - `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_REFRESH_TOKEN`
  - `SYNC_TRIGGER_SECRET` (used by Edge Function)
  - **Current Status:** ⚠️ Awaiting eBay approval + token

### ✅ Repository Status
- [ ] **Boss Listers MVP repo cloned locally or accessible:**
  - GitHub: `mjardin17/boss-listers-mvp` (branch: `feat/supabase-inventory`)
  - **Current Status:** ⚠️ Verify clone location
- [ ] **All dependencies up-to-date:**
  - `npm install` or `pnpm install`
  - No security advisories
  - **Current Status:** Need to verify

### ✅ Code Quality
- [ ] **All tests passing:**
  - Manual package unit tests
  - Connector honesty guards
  - `next build` compiles without errors
  - **Current Status:** ✅ Passing (as of 2026-07-28)
- [ ] **No hardcoded secrets in code:**
  - All API keys in `.env` or Vault
  - **Current Status:** ✅ Verified
- [ ] **TypeScript strict mode enforced:**
  - No `any` types
  - All props typed
  - **Current Status:** Need to verify

---

## PHASE 1: eBay Developer Approval (BLOCKERS)

### 🔴 BLOCKING: eBay Developer Account
- [ ] **Email from eBay arrived** (approval notification)
  - Expected: Confirmation of developer account
  - **Action:** Check email for eBay submission response
- [ ] **Once approved, complete OAuth consent flow:**
  - Go to: `https://auth.sandbox.ebay.com/oauth2/authorize` (or production)
  - Get `authorization_code`
  - Exchange for `refresh_token`
  - Store in Supabase Vault as `EBAY_REFRESH_TOKEN`
  - **Reference:** `inventory-sync/DEPLOY.md` step-by-step guide

### 🔴 BLOCKING: eBay API Credentials
- [ ] **Grab credentials from eBay Developer Portal:**
  - `EBAY_CLIENT_ID` → Vault `EBAY_CLIENT_ID`
  - `EBAY_CLIENT_SECRET` → Vault `EBAY_CLIENT_SECRET`
  - `EBAY_RUNAME` (if using Authorization Code Grant)
- [ ] **Set Vault secrets in Supabase:**
  ```bash
  supabase secrets set EBAY_CLIENT_ID=<value>
  supabase secrets set EBAY_CLIENT_SECRET=<value>
  supabase secrets set EBAY_REFRESH_TOKEN=<value>
  supabase secrets set SYNC_TRIGGER_SECRET=<random-secret>
  ```

---

## PHASE 2: Deploy Infrastructure (Edge Function)

### ✅ Supabase Edge Function Deployment
- [ ] **Deploy the ebay-sync Edge Function:**
  ```bash
  cd inventory-sync/
  supabase functions deploy ebay-sync
  ```
  - Verifies: Function compiles, connects to Supabase, respects RLS
- [ ] **Test the function manually:**
  ```bash
  supabase functions test ebay-sync
  ```
  - Expected: Returns 200 (if eBay creds are valid) or 401 (if missing)
- [ ] **Verify pg_cron schedule is active:**
  - Check Supabase SQL Editor: `SELECT * FROM cron.job WHERE jobname LIKE '%ebay%';`
  - Expected: 1 row, status = active, every 15 minutes
  - **Current Status:** ✅ Scheduled in migration 0002

---

## PHASE 3: Deploy Frontend (Vercel)

### ✅ Boss Listers App on Vercel
- [ ] **Install Vercel CLI:**
  ```bash
  npm install -g vercel
  vercel login
  ```
- [ ] **Deploy boss-listers-mvp:**
  ```bash
  cd <boss-listers-mvp-path>
  vercel
  ```
  - Follow prompts: Connect to GitHub, set project name, environment variables
- [ ] **Set Vercel environment variables:**
  ```
  SUPABASE_URL=https://irslzufsqjveyibkfjtz.supabase.co
  SUPABASE_ANON_KEY=<your-anon-key>
  ```
  - Get from: Supabase console > Project Settings > API
- [ ] **Trigger deployment:**
  ```bash
  vercel --prod
  ```
- [ ] **Verify deployment:**
  - Check: `https://<your-project>.vercel.app`
  - Expected: App loads, Channels page shows status pills

### ✅ Website Integration (Cloudflare Pages)
- [ ] **Update `index.html` with live Supabase credentials:**
  - Lines ~968-969: Replace `${SUPABASE_URL}` and `${SUPABASE_ANON_KEY}`
  - Source: Supabase console > Project Settings > API
- [ ] **Deploy website to Cloudflare Pages:**
  ```bash
  git add index.html
  git commit -m "update: live Supabase credentials in website"
  PUSH_NOW.bat  # Uses push_bypass.py
  ```
  - Cloudflare auto-deploys on push
- [ ] **Set Cloudflare Pages environment variables (if using Functions):**
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - Project Settings > Environment > Production

---

## PHASE 4: End-to-End Testing

### 🧪 Integration Test Flow
1. **List an item on eBay** (manually or via eBay seller app)
2. **Wait 15-20 minutes** for eBay→Supabase sync
3. **Verify item appears on website:**
   - Open: `https://jardins-outpost.pages.dev`
   - Navigate to: "Shop The Inventory" section
   - Expected: Item visible with price, quantity, image
4. **Edit item in Boss Listers:**
   - Open: `https://<boss-listers>.vercel.app`
   - Go to: Channels tab
   - Manual listing: Create a listing, export to CSV
   - Expected: CSV download works, copy-paste buttons work
5. **Test Realtime updates:**
   - Open website in browser 1
   - Update price/quantity in Boss Listers (browser 2)
   - Expected: Website updates within 1 second (Realtime subscription)

### 🧪 Channels Page Verification
- [ ] **All 8 platforms show correct status:**
  - eBay: "AWAITING_APPROVAL" (until OAuth completes)
  - Poshmark: "NOT_CONNECTED" or manual export ready
  - Mercari, Depop, Grailed, Etsy, Shopify, TikTok Shop: Same
- [ ] **Manual export connector works:**
  - Select platform (e.g., Poshmark)
  - Generate listing package (title + description + keywords)
  - Copy or download CSV
  - Expected: Platform-optimized text (within character limits)
- [ ] **Test Connection button works:**
  - Click "Test Connection" on eBay
  - Expected: Shows status (connected/needs auth/error)

### 🧪 Supabase Data Quality
- [ ] **Check products table:**
  ```sql
  SELECT COUNT(*) FROM public.products WHERE source='ebay';
  ```
  - Expected: > 0 if eBay sync ran
- [ ] **Check sync_logs:**
  ```sql
  SELECT * FROM public.sync_logs ORDER BY created_at DESC LIMIT 5;
  ```
  - Expected: Rows showing sync attempts with status
- [ ] **Check Realtime subscriptions:**
  - Website console: Should show Realtime listener active
  - Modify a row in `products` via Supabase SQL Editor
  - Expected: Website updates without page refresh

---

## PHASE 5: Launch Sign-Off

### 🎯 Final Checklist Before Going Live
- [ ] **All 3 deployment targets verified:**
  - ✅ Supabase Edge Function live and running
  - ✅ Boss Listers app live on Vercel
  - ✅ Website live on Cloudflare Pages
- [ ] **eBay OAuth flow completed (if available):**
  - ✅ refresh_token in Vault
  - ✅ Edge Function can authenticate
  - ✅ First sync successful
- [ ] **Inventory is visible end-to-end:**
  - ✅ eBay items synced to `products` table
  - ✅ Website "Shop The Inventory" loads items
  - ✅ Boss Listers dashboard can edit items
- [ ] **Manual platform exports working:**
  - ✅ Channels page loads
  - ✅ Manual export connector generates listings
  - ✅ CSV download works
- [ ] **No hardcoded secrets visible:**
  - ✅ All env vars in .env (git-ignored)
  - ✅ Supabase secrets in Vault (never logged)
  - ✅ Code review: no API keys in commits

### 📢 Launch Announcement (Once Complete)
- [ ] **Update CLAUDE.md:**
  - Mark Boss Listers as "LIVE"
  - Link to deployment URLs
  - Note any manual setup required for users
- [ ] **Email to stakeholders:**
  - eBay sync live (15-min polling)
  - Boss Listers app deployed
  - Manual export available for other platforms
  - Next: Integrate real platform APIs as they're available
- [ ] **Git commit:**
  ```bash
  git commit -m "[CLAUDE] docs: Boss Listers live on Vercel + Cloudflare"
  ```

---

## Deployment URLs (Once Live)

| Component | URL | Status |
|-----------|-----|--------|
| Boss Listers Dashboard | `https://<project>.vercel.app` | Awaiting deploy |
| Live Inventory Widget | `https://jardins-outpost.pages.dev#shop` | Live (integration pending) |
| eBay Sync Function | `https://irslzufsqjveyibkfjtz.supabase.co/functions/v1/ebay-sync` | Deployed (awaiting eBay auth) |
| API Endpoint (products) | `https://jardins-outpost.pages.dev/api/products` | Live (Cloudflare Function) |

---

## Troubleshooting Quick Links

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Vercel deploy fails | Missing env vars | Set `SUPABASE_URL` + `SUPABASE_ANON_KEY` in Vercel |
| Sync function 401 | Missing eBay credentials | Complete OAuth consent flow, store refresh_token in Vault |
| Website shows "Loading..." | Supabase anon key invalid | Verify key in `index.html` matches Supabase console |
| Realtime not working | RLS blocking anon reads | Check `products` table grants (migration 0004) |
| Manual export not generating | API route 404 | Verify `/api/channels/manual-package` route in Next.js |

---

## Notes
- **eBay developer approval** is the primary blocker. Check email immediately.
- **Vercel deployment** is straightforward once repo is cloned.
- **No changes to code required** — infrastructure is production-ready.
- **First sync** may take 15-20 minutes after eBay auth completes.
- **Manual exports** work immediately (no external APIs required).

---

**Next Session Task:** Check eBay developer email, complete OAuth flow, deploy Edge Function, trigger first sync test.
