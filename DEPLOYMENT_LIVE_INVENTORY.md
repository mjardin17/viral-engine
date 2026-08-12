# Live Inventory System — Deployment Checklist

## ✅ Already Done
- [x] Supabase project created + migrations applied (0001-0004)
- [x] eBay API credentials stored in Supabase Vault
- [x] Supabase Edge Function (ebay-sync) scheduled via pg_cron every 15 mins
- [x] Website (index.html) wired to Supabase credentials
- [x] Cloudflare Pages Function (/api/products) ready to serve
- [x] MISSION_BOARD.json dispatched to Council

## 🚀 Final Steps (2 minutes)

### 1. Deploy to Cloudflare Pages
Your website is already on GitHub at `C:\Users\jjard\claude\video-bot-pipeline`.

Go to **dash.cloudflare.com** → Pages → Connect Git → select viral-engine repo

Set environment variables:
```
SUPABASE_URL = https://irslzufsqjveyibkfjtz.supabase.co
SUPABASE_ANON_KEY = sb_publishable_HV03fWT-xFr4mB1x3AGlcg_a3JbBtwA
```

Click Deploy. Done in ~2 mins.

### 2. Deploy Boss Listers to Vercel
Go to **vercel.com** → New Project → import viral-engine GitHub repo

Set environment variables (same as above):
```
SUPABASE_URL = https://irslzufsqjveyibkfjtz.supabase.co
SUPABASE_ANON_KEY = sb_publishable_HV03fWT-xFr4mB1x3AGlcg_a3JbBtwA
```

Click Deploy. Done in ~1 min.

## 🎯 After Deployment

**Your system is now live:**
1. eBay items sync to Supabase every 15 mins (automatic)
2. Website's "Shop The Inventory" section pulls live data from Supabase
3. Boss Listers dashboard (Vercel) reads/writes to same `products` table
4. Edit a price in Boss Listers → website updates instantly via Realtime subscription
5. Item sells on eBay → Supabase updates → website removes it automatically

## 📊 Verify It's Working

1. Add an item to your eBay active listings
2. Wait up to 15 minutes for the sync
3. Check https://jardins-outpost.pages.dev#inventory → should see it
4. Open https://boss-listers.vercel.app → should see it there too
5. Edit the price in Boss Listers → website updates in real-time

## 🔧 Troubleshooting

**Products not showing?**
- Check Supabase → products table has rows (via Dashboard SQL Editor)
- Check Cloudflare Pages env vars are set correctly
- Wait 15 mins for first eBay sync to run

**Boss Listers can't connect?**
- Check Vercel env vars are set
- Check browser console for CORS errors
- Verify SUPABASE_URL + ANON_KEY are correct

**Prices not syncing?**
- Check Supabase → products table updated_at timestamp
- Open website in fresh browser (clear cache)
- Check browser console for Realtime subscription errors
