# Credential Setup Guide

## Quick Start

```bash
GET_CREDENTIALS.bat
```

This launches an interactive agent that:
1. Shows you exactly where to get each API key/token
2. Validates each credential against the actual API
3. Saves everything to `.env` automatically
4. Never stores credentials in git (`.env` is gitignored)

---

## What You Need

### 12 Live Platforms (API tokens required)

| # | Platform | Credential Type | Effort | Status |
|---|---|---|---|---|
| 1 | **Etsy** | OAuth Token | ⭐⭐ Easy | Takes 5 min |
| 2 | **Depop** | API Token | ⭐⭐ Easy | Takes 5 min |
| 3 | **Shopify** | Access Token | ⭐⭐⭐ Medium | Need store URL |
| 4 | **WooCommerce** | API Key:Secret | ⭐⭐⭐ Medium | Need WordPress admin |
| 5 | **Grailed** | API Key | ⭐⭐ Easy | Takes 5 min |
| 6 | **Vinted** | API Token | ⭐⭐ Easy | Takes 5 min |
| 7 | **Vestiaire** | API Token | ⭐⭐ Easy | Takes 5 min |
| 8 | **eBay** | OAuth Token | ⭐⭐⭐ Medium | Seller account required |
| 9 | **Facebook** | Graph API Token | ⭐⭐ Easy | Takes 5 min |
| 10 | **Mercado Libre** | OAuth Token | ⭐⭐ Easy | Takes 5 min |
| 11 | **Reverb.com** | API Token | ⭐⭐ Easy | Takes 5 min |
| 12 | **The RealReal** | API Token | ⭐⭐ Easy | Takes 5 min |

### 2 Stubs (Waiting for API access)

- **Mercari** — Waiting for official API documentation
- **Poshmark** — Waiting for API access approval

---

## Interactive Setup

### Start Collection

```bash
GET_CREDENTIALS.bat
```

### What Happens

The agent will:

1. **Show setup guide** for each platform
   - Link to developer docs
   - Step-by-step instructions
   - Where to find the token

2. **Ask for your token**
   - Paste the credential you copied

3. **Validate immediately**
   - Tests the token against the actual API
   - Confirms it works before saving
   - Lets you retry if invalid

4. **Save to .env**
   - All credentials stored securely
   - Git won't touch `.env` (gitignored)
   - Ready for agents to use

### Skip Anytime

Press Enter without typing to skip any platform. You can always run the setup again later.

---

## Single Platform Setup

If you just want to set up one platform:

```bash
GET_CREDENTIALS.bat etsy
```

Replaces `etsy` with any platform name (depop, shopify, etc.)

---

## Manual Setup (If Interactive Fails)

1. Get your tokens from each platform's developer docs
2. Create/edit `.env` file in the repo root:

```env
ETSY_TOKEN=your_etsy_token_here
DEPOP_TOKEN=your_depop_token_here
SHOPIFY_TOKEN=your_shopify_token_here
SHOPIFY_STORE_NAME=mystore.myshopify.com
# ... etc for all platforms
```

3. Save the file
4. Agents will automatically pick up the credentials

---

## Validation

After setup, run:

```bash
python test_credential_agent.py
```

Shows which platforms are configured and ready:

```
✓ etsy                 → Etsy                      [✓ CONFIGURED]
⊘ depop                → Depop                     [⊘ NOT SET]
```

---

## What Each Agent Does With Credentials

### Platform Sync Agent (every 120s)
- Uses credentials to post new items to all 12 platforms
- Automatically syncs inventory from Boss Listers

### Sales Tracker Agent (every 300s)
- Uses credentials to check each platform for sales
- Updates Boss Listers inventory when items sell

### Price Sync Agent (every 300s)
- Uses credentials to push price changes to all platforms
- Detects when you change prices in Boss Listers

---

## Troubleshooting

### "Credential validation failed"
- Token may be expired or revoked
- Try generating a new token on the platform's developer site
- Paste the new one and try again

### "No new sales detected"
- Platforms may not have any sales yet (normal)
- Check the agent logs in the terminal window

### "Missing credentials"
- Some platforms are optional — skip them if you don't use them
- Only platforms you configure will be synced

### ".env file not found"
- Run `GET_CREDENTIALS.bat` — it creates `.env` automatically
- Or manually create it in the repo root

---

## Security Notes

✅ **Never commit .env to git** — it's in `.gitignore`  
✅ **Credentials stay on your machine** — never sent to Claude or any server  
✅ **Each token is validated** — tests against real API before saving  
✅ **Easy to revoke** — delete tokens anytime from platform settings  

---

## Next Steps

1. Run `GET_CREDENTIALS.bat`
2. Collect credentials for platforms you use most (start with Etsy, Depop, Shopify)
3. Save the `.env` file
4. Watch the agents start syncing automatically

All 5 agents will automatically detect credentials in `.env` and begin working.

---

## Platform-Specific Notes

### Shopify
You need BOTH:
- `SHOPIFY_TOKEN` = Access token
- `SHOPIFY_STORE_NAME` = Your store URL (e.g., mystore.myshopify.com)

### WooCommerce
You need BOTH:
- `WOOCOMMERCE_KEY` = Consumer Key
- `WOOCOMMERCE_SECRET` = Consumer Secret
- `WOOCOMMERCE_URL` = Your store URL

### Facebook
- Graph API token works (User or Page token)
- Requires Pages permission to manage Marketplace listings

### eBay
- Must be a Seller account
- Requires OAuth approval on first use

---

## Logs

The credential collector logs all attempts to `credential_collection_log.txt`:

```
[2026-08-09T13:45:22.123456] ✓ etsy: ETSY_TOKEN configured and validated
[2026-08-09T13:45:45.654321] Skipped depop
[2026-08-09T13:46:10.987654] Session complete: 1 collected, 1 skipped
```

Use this to track what's been set up and what still needs attention.
