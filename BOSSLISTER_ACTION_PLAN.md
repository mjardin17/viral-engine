# Boss Listers — Immediate Action Plan 🚀

**Status:** Everything is built. eBay approval is the only blocker.  
**Timeline:** Deploy-ready once eBay email arrives.  
**Owner:** Josh Jardin

---

## ⏳ RIGHT NOW (Do This First)

### Step 1: Check eBay Developer Email
- **Action:** Go to email inbox
- **Look for:** Message from eBay with subject like "Developer Account Approved" or "OAuth Credentials Ready"
- **Expected:** Email with API keys, sandbox endpoints, and developer portal link
- **⚠️ If NOT arrived yet:** Mark calendar for 1-2 day follow-up. Meanwhile, proceed with optional setup below.

---

## 🔧 ONCE eBay EMAIL ARRIVES (Complete in ~30 minutes)

### Step 2: Get eBay OAuth Token
1. **Log into eBay Developer Portal**
   - Go to: https://developer.ebay.com
   - Use your developer account credentials

2. **Locate Your Application**
   - Find the app you created for the API integration
   - Copy: `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET`

3. **Complete OAuth Consent Flow**
   - Go to: `https://auth.sandbox.ebay.com/oauth2/authorize?client_id=<EBAY_CLIENT_ID>&response_type=code&redirect_uri=https://localhost:3000/oauth&scope=...`
   - (Exact URL in inventory-sync/DEPLOY.md)
   - **Accept** the authorization
   - **Get:** authorization_code from redirect URL
   - **Exchange code for refresh_token** (using Python script or REST call — see DEPLOY.md)

4. **Store Secrets in Supabase**
   ```bash
   # From C:\Users\jjard\claude\video-bot-pipeline\inventory-sync\
   supabase secrets set EBAY_CLIENT_ID=<your-client-id>
   supabase secrets set EBAY_CLIENT_SECRET=<your-client-secret>
   supabase secrets set EBAY_REFRESH_TOKEN=<your-refresh-token>
   supabase secrets set SYNC_TRIGGER_SECRET=<random-secret-here>
   ```

---

## 🚀 AFTER eBay SETUP (Deploy Infrastructure)

### Step 3: Deploy eBay Sync Edge Function
```bash
cd C:\Users\jjard\claude\video-bot-pipeline\inventory-sync
supabase functions deploy ebay-sync
```
- Expected output: "Function deployed successfully"
- Test it: Open Supabase console → Functions → ebay-sync → Test

### Step 4: Deploy Boss Listers App
```bash
cd C:\Users\jjard\claude\boss-listers-mvp\boss-listers-mvp
npm install
npm run build
```

**Choose ONE deployment target:**

#### Option A: Deploy to Vercel (RECOMMENDED)
```bash
npm install -g vercel
vercel login
vercel --prod
```
- Sets up GitHub connection
- Prompts for env vars: `SUPABASE_URL` and `SUPABASE_ANON_KEY`
- Get values from: https://app.supabase.com → Project Settings → API
- Live URL: `https://boss-listers.vercel.app` (or your project name)

#### Option B: Deploy to Cloudflare Pages
```bash
npm run deploy
```
- Uses `wrangler.toml` configuration
- Live URL: `https://boss-listers.<account>.pages.dev`

### Step 5: Deploy Website with Live Supabase Credentials
```bash
# Edit the website file
cd C:\Users\jjard\claude\video-bot-pipeline

# Update index.html with real Supabase credentials
# Search for lines ~968-969 and replace:
# OLD: ${SUPABASE_URL} → NEW: https://irslzufsqjveyibkfjtz.supabase.co
# OLD: ${SUPABASE_ANON_KEY} → NEW: <your-anon-key-from-supabase>

# Commit and push
git add index.html
git commit -m "[CLAUDE] update: live Supabase credentials in website"
PUSH_NOW.bat

# Cloudflare auto-deploys on git push ✅
```

---

## ✅ VERIFY IT WORKS (End-to-End Test)

### Test 1: eBay Sync
1. **List an item on eBay** (use sandbox if in testing, or real account)
2. **Wait 15-20 minutes** for the pg_cron trigger to run
3. **Check Supabase SQL Editor:**
   ```sql
   SELECT * FROM public.sync_logs ORDER BY created_at DESC LIMIT 1;
   ```
   - Expected: Row showing sync attempt, status = "success"
4. **Check products table:**
   ```sql
   SELECT COUNT(*) FROM public.products WHERE source='ebay';
   ```
   - Expected: > 0 if sync ran

### Test 2: Website Live Inventory
1. **Open:** https://jardins-outpost.pages.dev
2. **Scroll to:** "Shop The Inventory" section
3. **Expected:** See eBay items listed with images, prices, quantities
4. **Realtime test:** Open Supabase SQL Editor in another tab
   - Update a product price: `UPDATE products SET price = 99.99 WHERE id = '...' AND source='ebay';`
   - Website should update within 1 second (Realtime subscription)

### Test 3: Boss Listers Dashboard
1. **Open:** https://boss-listers.vercel.app (or your deployment URL)
2. **Navigate to:** "Channels" tab
3. **Expected:**
   - eBay shows: "CONNECTED" (after OAuth completes)
   - Poshmark/Mercari/etc: Show "NOT_CONNECTED" or "MANUAL_EXPORT_READY"
4. **Test manual export:**
   - Select Poshmark
   - Click "Generate Listing Package"
   - Expected: Poshmark-optimized title + description + keywords
   - Copy to clipboard or download CSV

---

## 📊 Launch Sign-Off Checklist

Once all tests pass:

- [ ] eBay sync Edge Function running and pulling inventory
- [ ] Website "Shop The Inventory" shows live items
- [ ] Boss Listers dashboard loads and channels page functional
- [ ] Manual exports working (at least one platform tested)
- [ ] Realtime updates verified (instant when Supabase data changes)
- [ ] No hardcoded secrets in any files or commits
- [ ] All 3 deployment targets live and accessible

**When all ✅:** 
1. Update CLAUDE.md: Mark Boss Listers as "LIVE"
2. Git commit final changes
3. Send announcement: Boss Listers is live!

---

## Troubleshooting Quick Reference

| Error | Fix |
|-------|-----|
| `eBay API 401 Unauthorized` | Refresh token expired or invalid. Re-run OAuth consent flow, update Vault secret. |
| Website shows "Loading..." forever | Check browser console for errors. Verify SUPABASE_URL/ANON_KEY in index.html. |
| Boss Listers `/api/channels` returns 404 | Rebuild: `npm run build`. Deploy: `wrangler pages deploy out`. |
| Realtime updates not working | Check Supabase console: RLS policy on `products` table. Should allow anon SELECT. |
| Manual export missing keywords | Check `manualPackage.js` — ensure keyword extraction logic is working. |

---

## Important Links

| Resource | URL |
|----------|-----|
| Supabase Project | https://app.supabase.com → Select "Boss listers prod" |
| eBay Developer Portal | https://developer.ebay.com |
| Boss Listers Repo | https://github.com/mjardin17/boss-listers-mvp |
| Deployment Docs (Full) | `inventory-sync/DEPLOY.md` |
| Launch Checklist (Full) | `BOSSLISTER_LAUNCH_CHECKLIST.md` |

---

## Success Criteria

✅ **You'll know it's working when:**
1. Item listed on eBay appears on the website within 20 minutes
2. Price/quantity changes sync instantly (Realtime)
3. Boss Listers dashboard can edit items and export to platforms
4. All 3 apps load without errors
5. No sensitive data in logs or commits

---

**Questions?** Check `inventory-sync/DEPLOY.md` for detailed step-by-step instructions.  
**Ready to launch?** Follow this plan in order. eBay approval is the only real blocker.
