# Empire OS — API Credentials Checklist

Master list of all real tokens needed for full 14-platform operation + expansion.

---

## TIER 1: CORE 14 PLATFORMS (Orchestrator Priority)

### PRODUCT MARKETPLACES (7)

#### ✅ eBay (LIVE)
- `EBAY_CLIENT_ID` — App ID from eBay Developer Portal ✓
- `EBAY_CLIENT_SECRET` — App Secret ✓
- `EBAY_REFRESH_TOKEN` — OAuth refresh token ✓
- `EBAY_ENVIRONMENT` — "production" ✓
- **Get it:** https://developer.ebay.com/

#### ⚠️ Etsy (BUILT, NEEDS TOKEN)
- `ETSY_KEYSTRING` — API keystring
- `ETSY_SHARED_SECRET` — API shared secret
- `ETSY_SHOP_ID` — Your Etsy shop numeric ID
- `ETSY_ACCESS_TOKEN` — OAuth access token (currently placeholder)
- **Get it:** https://www.etsy.com/developers/
- **Status:** App pending approval OR already approved (verify)

#### ⚠️ Facebook Marketplace (BUILT, NEEDS TOKEN)
- `FB_APP_ID` — Facebook App ID (have partial)
- `FB_APP_SECRET` — Facebook App Secret (have partial)
- `FB_PAGE_ID` — Your Facebook Page numeric ID
- `FB_PAGE_ACCESS_TOKEN` — Page-scoped access token (NOT user token)
- **Get it:** https://developers.facebook.com/ → Business Manager
- **Status:** App exists, needs Page token

#### ⚠️ Bonanza (BUILT, NEEDS TOKEN)
- `BONANZA_ACCESS_TOKEN` — OAuth access token
- **Get it:** https://api.bonanza.com/ (OAuth flow)
- **Status:** Not yet set

#### ⚠️ Shopify (BUILT, NEEDS TOKEN)
- `SHOPIFY_STORE_URL` — Your Shopify store (mystore.myshopify.com)
- `SHOPIFY_API_KEY` — Admin API key
- `SHOPIFY_ACCESS_TOKEN` — Admin API access token
- **Get it:** https://admin.shopify.com/ → Settings → Apps & integrations → Admin API
- **Status:** Not yet set

#### ✅ Poshmark (BROWSER AUTH - LIVE)
- `POSHMARK_USERNAME` — Account username ✓
- `POSHMARK_PASSWORD` — Account password ✓
- **Status:** Browser automation ready

#### ✅ Mercari (BROWSER AUTH - LIVE)
- `MERCARI_USERNAME` — Account username ✓
- `MERCARI_PASSWORD` — Account password ✓
- **Status:** Browser automation ready

---

### BOOK PLATFORMS (4)

#### ⚠️ Amazon KDP (BUILT, MANUAL)
- `KDP_ACCOUNT_EMAIL` — Your Amazon account email
- Browser automation required (no API)
- **Get it:** https://kdp.amazon.com/
- **Status:** Manual upload path implemented

#### ⚠️ Draft2Digital (BUILT, NEEDS TOKEN)
- `D2D_API_KEY` — API key
- **Get it:** https://www.draft2digital.com/ → Account → API
- **Note:** D2D doesn't have public API (as of research) — manual upload
- **Status:** Connector built, needs verification

#### ⚠️ Payhip (BUILT, NEEDS TOKEN)
- `PAYHIP_API_KEY` — API key for products
- `PAYHIP_SELLER_ID` — Your seller ID
- **Get it:** https://payhip.com/ → Account → API
- **Status:** Connector built, needs testing

#### ✅ Etsy Digital (Etsy credentials above)
- Uses same `ETSY_*` credentials as marketplace
- **Status:** Ready (waiting on Etsy token)

---

### SOCIAL NETWORKS (4)

#### ✅ Instagram (LIVE)
- `IG_ACCESS_TOKEN` — User access token ✓
- `IG_USER_ID` — Your Instagram numeric user ID ✓
- **Status:** Publishing working live (posts Reels)
- **Refresh:** Token expires in 60 days — set refresh reminder around day 45

#### ⚠️ TikTok (BUILT, NEEDS TOKEN)
- `TIKTOK_ACCESS_TOKEN` — OAuth access token
- `TIKTOK_VIDEO_ID` — Video ID reference (auto-generated)
- **Get it:** https://developer.tiktok.com/ → OAuth
- **Status:** Connector built, needs testing
- **Note:** No official TikTok Shorts API — uses video upload endpoint

#### ⚠️ Facebook (BUILT, NEEDS TOKEN)
- `FB_PAGE_ACCESS_TOKEN` — Page token (same as Marketplace above)
- **Status:** Shares token with Marketplace
- **Note:** Marketplace and Page use same credentials

#### ✅ Pinterest (PLACEHOLDER "skip")
- `PINTEREST_ACCESS_TOKEN` — Pinterest API token
- `PINTEREST_USER_ID` — Your numeric user ID
- **Get it:** https://developers.pinterest.com/ → OAuth
- **Status:** Connector built, token currently "skip" (placeholder)

---

## TIER 2: ADDITIONAL PLATFORMS (To Expand)

### More Marketplaces

#### Depop (Browser automation ready)
- `DEPOP_USERNAME` — Account username
- `DEPOP_PASSWORD` — Account password

#### Vinted (Browser automation ready)
- `VINTED_USERNAME` — Account username
- `VINTED_PASSWORD` — Account password

#### Vestiaire Collective (Browser automation ready)
- `VESTIAIRE_USERNAME` — Account username
- `VESTIAIRE_PASSWORD` — Account password

#### Grailed (Stub ready for API)
- `GRAILED_API_KEY` — API key (if public API exists)

#### MercadoLibre (Stub ready for API)
- `MERCADO_LIBRE_API_KEY` — API key
- `MERCADO_LIBRE_SELLER_ID` — Your seller ID

#### Reverb (Music gear - Stub ready)
- `REVERB_API_KEY` — API key
- `REVERB_SHOP_ID` — Your shop ID

#### RealReal (Luxury resale)
- `REALREAL_API_KEY` — API key
- `REALREAL_CONSIGNOR_ID` — Your consignor ID

---

### More Social Networks

#### TikTok Business (Higher limits than creator account)
- `TIKTOK_BUSINESS_ACCESS_TOKEN` — Business account token
- `TIKTOK_AD_ACCOUNT_ID` — Ad account for analytics

#### YouTube Shorts (Already have channel_uploader.py)
- Reuses `token_gg.pickle` from channel authentication
- **Status:** Already working for full videos, Shorts auto-generated

#### LinkedIn
- `LINKEDIN_ACCESS_TOKEN` — OAuth token
- `LINKEDIN_ORG_ID` — Organization ID

#### Discord (For announcements/alerts)
- `DISCORD_BOT_TOKEN` — Bot token
- `DISCORD_CHANNEL_ID` — Channel to post to

#### Reddit (Social proof/engagement)
- `REDDIT_CLIENT_ID` — App client ID
- `REDDIT_CLIENT_SECRET` — App client secret
- `REDDIT_SUBREDDIT` — Target subreddit

---

### More Book Platforms

#### Google Play Books
- `GOOGLE_PLAY_DEVELOPER_ACCOUNT` — Developer account access
- Manual upload via Play Console

#### Apple Books
- `APPLE_BOOKS_ACCOUNT` — iTunes Connect account
- Manual or via Aggregator (Draft2Digital, etc.)

#### Smashwords
- `SMASHWORDS_API_KEY` — API key (if available)
- Manual upload otherwise

#### Gumroad
- `GUMROAD_API_TOKEN` — API token
- `GUMROAD_PRODUCT_IDS` — Your product IDs

#### Leanpub
- `LEANPUB_API_KEY` — API key
- Manual or bulk import

---

### Merch (Print-on-Demand)

#### Printful
- `PRINTFUL_API_KEY` — API key
- `PRINTFUL_WAREHOUSE_ID` — Warehouse ID
- **Get it:** https://www.printful.com/settings/api

#### Printify
- `PRINTIFY_API_KEY` — API key
- `PRINTIFY_SHOP_ID` — Shop ID
- **Get it:** https://printify.com/app/account/api

#### Gooten
- `GOOTEN_API_KEY` — API key
- **Get it:** https://www.gooten.com/

---

## CURRENT STATUS

### ✅ Already Set (Ready to use)
- eBay (production)
- Instagram (live)
- Whatnot (browser auth)
- Poshmark (browser auth)
- Mercari (browser auth)
- Facebook email (browser auth)

### ⚠️ Built but Needs Token
- Etsy (pending app approval OR token not configured)
- Facebook Marketplace (needs FB_PAGE_ACCESS_TOKEN)
- Bonanza
- Shopify
- TikTok
- Pinterest (currently "skip")
- Payhip
- D2D

### 🔲 Built but Not Started
- LinkedIn
- Discord
- Reddit
- Reverb
- RealReal
- Grailed
- MercadoLibre
- Vinted
- Vestiaire
- Depop

---

## PRIORITY ACTION LIST

**To make Orchestrator fully operational (14 platforms → revenue):**

1. ✅ eBay — DONE
2. ⚠️ Etsy — Get token OR confirm approval status
3. ⚠️ Facebook — Get FB_PAGE_ACCESS_TOKEN
4. ✅ Bonanza — Get BONANZA_ACCESS_TOKEN (easy OAuth)
5. ⚠️ Shopify — Get SHOPIFY_ACCESS_TOKEN (if you use Shopify)
6. ✅ Poshmark — DONE
7. ✅ Mercari — DONE
8. ⚠️ KDP — Manual OK (submit via UI)
9. ⚠️ Draft2Digital — Get D2D_API_KEY
10. ⚠️ Payhip — Get PAYHIP_API_KEY
11. ✅ Etsy Digital — Same as Etsy
12. ✅ Instagram — DONE
13. ⚠️ TikTok — Get TIKTOK_ACCESS_TOKEN
14. ⚠️ Pinterest — Get PINTEREST_ACCESS_TOKEN

---

## TOKEN ACQUISITION SCRIPT

Create `.env` entries in this order:

```bash
# PRODUCTS (7)
EBAY_CLIENT_ID=...
EBAY_CLIENT_SECRET=...
EBAY_REFRESH_TOKEN=...
ETSY_KEYSTRING=...
ETSY_SHARED_SECRET=...
ETSY_SHOP_ID=...
ETSY_ACCESS_TOKEN=...
FB_PAGE_ID=...
FB_PAGE_ACCESS_TOKEN=...
BONANZA_ACCESS_TOKEN=...
SHOPIFY_STORE_URL=...
SHOPIFY_ACCESS_TOKEN=...

# BOOKS (4)
KDP_ACCOUNT_EMAIL=...
D2D_API_KEY=...
PAYHIP_API_KEY=...
PAYHIP_SELLER_ID=...

# SOCIAL (4)
IG_ACCESS_TOKEN=...
IG_USER_ID=...
TIKTOK_ACCESS_TOKEN=...
PINTEREST_ACCESS_TOKEN=...
PINTEREST_USER_ID=...
```

**Then:** `python orchestrator.py` with `dry_run=True` first to test.

---

## Notes

- Browser auth (Poshmark, Mercari, Depop, etc.) requires stored session cookies — handled by `lib/browser_connectors.py`
- Most OAuth tokens expire — set calendar reminders for refresh (typically 30-90 days)
- Some platforms (KDP, D2D) have no official API — manual uploads or web scraping required
- Pinterest token is currently "skip" — set real token or remove from orchestrator
- TikTok's official Shorts API is limited — may need video upload + manual shorts creation
