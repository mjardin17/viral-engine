# eBay OAuth Integration Setup Guide

**Status:** ✅ Code ready, awaiting developer credentials
**API:** eBay REST API v2 (Inventory & Fulfillment)
**Auth:** OAuth 2.0 with refresh tokens
**Integration:** Full listing management + price sync + sales tracking

---

## Prerequisites Checklist

- [ ] eBay Developer Account (apply at developer.ebay.com)
- [ ] eBay Business Account (required for selling)
- [ ] Client ID + Client Secret from developer.ebay.com
- [ ] Redirect URI set in app settings

---

## Step 1: Create eBay Developer Account

1. Go to https://developer.ebay.com
2. Sign in with your eBay account (or create new)
3. Click "Applications & Certificates" → "Keys"
4. Create new app:
   - **App name:** "Empire OS Sales Pipeline"
   - **App type:** "Merchant"
   - **Description:** "Multi-platform inventory management system"

---

## Step 2: Get OAuth Credentials

After app is created:

1. Click on your app name in "Application Keys"
2. Copy the following:
   - **Client ID:** `YOUR_CLIENT_ID_HERE`
   - **Client Secret:** `YOUR_CLIENT_SECRET_HERE`

3. Go to "Auth & Permissions" tab
4. Under "Redirect URIs for Production" add:
   - `http://localhost:8080/ebay_oauth`
   - `http://localhost:8080/ebay_callback`

5. Under "OAuth scope" select:
   - ✅ `https://api.ebay.com/oauth/api_scope/sell.inventory`
   - ✅ `https://api.ebay.com/oauth/api_scope/sell.fulfillment`
   - ✅ `https://api.ebay.com/oauth/api_scope/sell.account`

---

## Step 3: Configure .env File

Add these to `.env`:

```bash
# eBay OAuth Credentials
EBAY_CLIENT_ID=YOUR_CLIENT_ID_HERE
EBAY_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
EBAY_SANDBOX_MODE=false  # Set to 'true' for testing

# eBay Redirect URI (don't change unless using different port)
EBAY_REDIRECT_URI=http://localhost:8080/ebay_oauth
```

**⚠️ SECURITY:** Never commit .env to git. Add to .gitignore if not already there.

---

## Step 4: Initial OAuth Authentication

Run the authentication script:

```bash
python agents/ebay_auth_agent.py --authenticate
```

This will:
1. Print an authorization URL
2. Open URL in your browser
3. You approve the permissions
4. Browser redirects to callback with auth code
5. Script exchanges code for tokens
6. Saves refresh token securely to `~/.ebay_credentials.json`

**Tokens expire every 2 hours, but refresh tokens are permanent.**

---

## Step 5: Verify Connection

Test that OAuth is working:

```bash
python agents/ebay_auth_agent.py --test
```

Expected output:
```
✅ eBay OAuth verified
User eBay Account: [your_username]
Active listings: 5
Total inventory: 12 items
```

---

## Step 6: Wire into Platform Sync Agent

The Platform Sync Agent will auto-detect eBay credentials and:

1. **Create inventory items** from Boss Listers
2. **List them on eBay** with auto-calculated prices
3. **Monitor for sales** and update inventory
4. **Sync prices** across all platforms

No additional setup needed—agent auto-activates when credentials are present.

---

## Features Enabled After Setup

### ✅ Automatic Listing Creation
```
Boss Listers product
    ↓
eBay inventory item created (via API)
    ↓
eBay listing published (auto-priced)
    ↓
Live on eBay within 2 minutes
```

### ✅ Price Sync
```
Josh updates price in Boss Listers
    ↓
Price Sync Agent detects change
    ↓
Automatically updates eBay listing price
    ↓
All platforms synchronized
```

### ✅ Sales Monitoring
```
Item sells on eBay
    ↓
Sales Tracker Agent pulls order data
    ↓
Auto-updates Boss Listers inventory (marks as "sold")
    ↓
Auto-delists from other platforms (if qty = 0)
```

### ✅ Multi-Platform Pricing Intelligence
```
eBay data + Whatnot + Facebook + Mercari + others
    ↓
Price Sync Agent analyzes competing prices
    ↓
Recommends optimal pricing per platform
    ↓
Maximizes profit across all channels
```

---

## Troubleshooting

### "Invalid OAuth token"
- Token may have expired
- Run `python agents/ebay_auth_agent.py --refresh` to force refresh
- Or re-authenticate: `python agents/ebay_auth_agent.py --authenticate`

### "Client ID / Secret mismatch"
- Verify credentials in `.env` are copied exactly (no extra spaces)
- Check that you're using Production credentials, not Sandbox

### "Listings not appearing"
- Check eBay seller account settings (automatic approval may be disabled)
- Verify shipping policies and return policies are set in eBay account
- Run `python agents/ebay_api_test.py` to test API connectivity

### OAuth redirect URI not working
- Make sure port 8080 is not blocked by firewall
- Verify redirect URI in eBay app settings exactly matches `.env`

---

## Files Created

- `lib/ebay_oauth_handler.py` — OAuth 2.0 authentication
- `lib/ebay_api_connector.py` — Listing/inventory management
- `agents/ebay_auth_agent.py` — Setup & token management
- `~/.ebay_credentials.json` — Secure token storage (created after auth)
- `EBAY_SETUP_GUIDE.md` — This guide

---

## Integration Points

| Agent | Integration | What Happens |
|-------|---|---|
| Platform Sync | Auto-list to eBay | Creates listings from Boss Listers inventory |
| Sales Tracker | Monitor eBay sales | Pulls orders, updates inventory when sold |
| Price Sync | Update eBay prices | Syncs price changes across all platforms |
| Whatnot Specialist | Pricing intelligence | Uses eBay data for optimal auction reserve pricing |
| Scanner Uploader | Scan → eBay | Scanned products auto-list on eBay |

---

## Revenue Potential

### eBay Channel Benchmarks
- **Fixed-price listings:** 1.0-1.5x product cost
- **Auction listings:** 1.5-2.5x product cost (competitive bidding)
- **New vs Used:** New items command 20-40% premium
- **Shipping:** Build in shipping cost + handling fee

### Example: $50 Product
```
Platform       | Sell Price | Profit
---            | ---        | ---
Facebook       | $75        | $25
Mercari        | $71        | $21
eBay Fixed     | $75        | $25
eBay Auction   | $110-130   | $60-80
Whatnot Auction| $130-150   | $80-100
```

**Multi-platform strategy:** List on eBay auction for 2.5x premium,
fixed-price on Facebook/Mercari for volume.

---

## Best Practices

### Pricing Strategy
1. **High-value collectibles** → eBay Auction (competitive bidding premium)
2. **Mid-tier items** → eBay Fixed + Facebook (volume + cash)
3. **Bulk items** → Mercari + Poshmark (quick turnover)

### Listing Optimization
- **Title:** Include brand, condition, key features (eBay has 80-char limit)
- **Photos:** 10-12 high-quality images (eBay allows 12 max)
- **Description:** Condition, authenticity guarantee, shipping policy
- **Keywords:** Use eBay category keywords for better search visibility

### Policy Setup
Before auto-listing is enabled, configure in your eBay account:
- **Shipping Policy:** Domestic + international rates
- **Return Policy:** Standard 30-day returns recommended
- **Payment Policy:** Accept all payment methods (eBay Payments)

These will be referenced when listing items via API.

---

## Testing with Sandbox

Before going production, test with eBay Sandbox:

1. Set `EBAY_SANDBOX_MODE=true` in `.env`
2. Go to https://developer.sandbox.ebay.com (Sandbox dashboard)
3. Create test OAuth credentials
4. Authenticate: `python agents/ebay_auth_agent.py --authenticate`
5. Test listings: `python agents/ebay_api_test.py`

Sandbox lets you test without risking real eBay listings.

---

## Next Steps

1. ✅ Create eBay Developer Account (apply if not done)
2. ✅ Get Client ID + Client Secret
3. ✅ Add credentials to `.env`
4. ✅ Run authentication: `python agents/ebay_auth_agent.py --authenticate`
5. ✅ Verify: `python agents/ebay_auth_agent.py --test`
6. ✅ Launch agents: `START_AGENTS.bat` (auto-detects eBay credentials)

Once complete, Platform Sync Agent will automatically create/manage eBay listings.

---

## Security Notes

- **Credentials file:** `~/.ebay_credentials.json` has restricted permissions (0600 — owner read/write only)
- **Never commit .env** to git repository
- **Refresh tokens** are long-lived; access tokens auto-refresh every 2 hours
- **OAuth flow** uses HTTPS; tokens never sent via unencrypted connection

---

## Support

**eBay API Docs:** https://developer.ebay.com/docs/sell/static/overview.html

**OAuth Help:** https://developer.ebay.com/docs/sell/static/ebay-rest-api-authentication.html

**Common Issues:** Check eBay developer forums or contact support@ebay.com

---

## Ready to Connect eBay?

Once you have your Client ID + Client Secret:

```bash
# 1. Add to .env
EBAY_CLIENT_ID=YOUR_ID
EBAY_CLIENT_SECRET=YOUR_SECRET

# 2. Authenticate
python agents/ebay_auth_agent.py --authenticate

# 3. Test connection
python agents/ebay_auth_agent.py --test

# 4. Run agents (auto-detects eBay)
START_AGENTS.bat
```

**eBay is now integrated with your 18-platform empire.** 🚀
