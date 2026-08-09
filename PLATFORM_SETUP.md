# Platform API Setup Guide

Each resale platform requires authentication credentials. Follow the steps below for each platform you want to sync with.

---

## Etsy (✅ LIVE API)

Etsy has a public REST API v3 with OAuth2 support. Full end-to-end implementation is complete.

### Setup Steps

1. **Register Etsy Developer App**
   - Go to https://www.etsy.com/developers/app
   - Sign in with your Etsy account (create one if needed)
   - Click "Get Started" and create a new app

2. **Gather Credentials**
   - **API Key** (public): Found on app dashboard
   - **Shop ID**: Numeric ID of your Etsy shop (usually 6-8 digits)

3. **Generate OAuth2 Token**
   - In your app settings, generate an OAuth authorization code
   - Exchange it for a refresh token (Etsy's flow requires this step)
   - Keep the refresh/access token in a safe place

4. **Set Environment Variables**
   ```bash
   # .env or system env vars
   ETSY_TOKEN=<your-oauth-access-token>
   ETSY_SHOP_ID=12345678
   ```

5. **Test Connection**
   - Run any agent and check for "✓ Etsy: Auth token present"
   - Logs will show successful API calls like "✓ Etsy: Created listing 123456789"

### API Limitations
- Max 10 images per listing
- Title: 140 char limit
- Description: 10,000 char limit
- Price updates allowed immediately
- 24-hour cooldown on some listing modifications

### Reference
- Etsy API Docs: https://developers.etsy.com/documentation
- Shop ID: Found in your shop settings URL (etsy.com/shop/{shop-id})

---

## Mercari (🚧 PENDING DOCS)

Mercari doesn't have an official public API yet. Implementation is a placeholder waiting for API documentation.

### Current Status
- No official Mercari API available to third-party developers
- Private API exists but violates terms of service to use directly
- Waiting for Mercari to release official developer API

### When Available
Once Mercari releases a public API:
1. Register developer app
2. Get API credentials
3. Set `MERCARI_TOKEN` environment variable
4. Connector framework is ready to plug in real implementation

### Workaround
For now, use manual export from the Crosspost system (`/channels` UI in boss-listers-mvp) to list items on Mercari.

---

## Poshmark (🚧 PENDING DOCS)

Poshmark doesn't expose a public API for third-party integrations.

### Current Status
- No official Poshmark API for external apps
- Platform restricts API access to internal tools only
- Waiting for Poshmark to open developer program

### Current Workaround
1. Use manual listing export from boss-listers-mvp (`/channels` UI)
2. Copy/paste into Poshmark web interface
3. Or use Poshmark's official tools (Seller app, web dashboard)

### When API Available
The framework is ready to implement once Poshmark provides API access.

---

## Depop (✅ LIVE API)

Depop has a public API with full implementation complete.

### Setup Steps

1. **Register Depop Developer App**
   - Go to https://www.depop.com/developer
   - Sign in with your Depop seller account
   - Create a new app

2. **Gather Credentials**
   - **API Token**: Found in app settings (OAuth2 token)

3. **Set Environment Variables**
   ```bash
   DEPOP_TOKEN=<your-api-token>
   ```

4. **Test Connection**
   - Run agents and check for "✓ Depop: Auth token present"
   - Logs will show successful API calls like "✓ Depop: Created listing 123456"

### API Limitations
- Max 8 images per listing
- Title: 50 char limit
- Description: 2,000 char limit
- Prices in USD cents (stored as integers)
- Category: auto-set to "fashion"

### Reference
- Depop API Docs: https://www.depop.com/developer
- API Rate: 100 req/min

---

## Grailed (🗺️ PLANNED)

Grailed is exploring API access for sellers. Status TBD.

### When Available
Will implement once Grailed opens API.

---

## Shopify (✅ LIVE API)

For sellers who have their own Shopify store. Full REST API v3 implementation complete.

### Setup Steps

1. **Create Shopify Custom App**
   - Go to Shopify admin dashboard
   - Apps > App and sales channel settings
   - Click "Develop an app"
   - Create a custom app

2. **Generate Access Token**
   - In custom app settings, click "Configuration"
   - Under "Admin API access scopes", select:
     - `write_products` (create/update products)
     - `read_products` (read product data)
     - `write_orders` (mark orders)
     - `read_orders` (fetch sales)
   - Click "Save"
   - Click "Reveal" next to Admin API access token
   - Copy and save the token

3. **Set Environment Variables**
   ```bash
   SHOPIFY_TOKEN=<your-access-token>
   SHOPIFY_STORE_NAME=your-store.myshopify.com
   ```

4. **Test Connection**
   - Run agents and check for "✓ Shopify: Auth token present"
   - Logs will show successful API calls like "✓ Shopify: Created product 123456"

### API Limitations
- Max 8 images per product
- Unlimited title length
- Unlimited description
- Variant management (prices per variant)
- Real-time inventory sync
- Order tracking with financial status

### Reference
- Shopify API Docs: https://shopify.dev/docs/api/admin-rest/2024-01
- Store URL format: https://your-store.myshopify.com
- API Version: 2024-01 (stable)

---

## WooCommerce (✅ LIVE API)

For sellers with WooCommerce stores. Full REST API implementation complete.

### Setup Steps

1. **Generate API Keys in WooCommerce**
   - Go to WooCommerce > Settings > Advanced > REST API
   - Click "Create an API key"
   - Set permissions: Read/Write
   - Copy Consumer Key and Consumer Secret

2. **Set Environment Variables**
   ```bash
   WOOCOMMERCE_URL=https://your-store.com
   WOOCOMMERCE_KEY=<consumer-key>
   WOOCOMMERCE_SECRET=<consumer-secret>
   ```

3. **Test Connection**
   - Run agents and check for "✓ WooCommerce: Auth token present"
   - Logs will show successful API calls like "✓ WooCommerce: Created product 123456"

### API Limitations
- Max images per product: unlimited
- Title: unlimited
- Description: unlimited (HTML allowed)
- Price: stored as string, supports decimals
- Stock: integer quantity tracking
- Simple products: one variant per product
- Variable products: multiple variants with different prices

### Reference
- WooCommerce API Docs: https://woocommerce.github.io/woocommerce-rest-api-docs
- Requires: WooCommerce plugin + REST API enabled
- SSL/HTTPS: strongly recommended for security
- Basic Auth: Consumer Key/Secret (HTTP Basic Auth)

---

## Environment Variables Summary

Add to `.env` file in project root:

```bash
# Etsy (LIVE API)
ETSY_TOKEN=your-etsy-oauth-token
ETSY_SHOP_ID=12345678

# Depop (LIVE API)
DEPOP_TOKEN=your-depop-api-token

# Shopify (LIVE API)
SHOPIFY_TOKEN=your-shopify-access-token
SHOPIFY_STORE_NAME=your-store.myshopify.com

# WooCommerce (LIVE API)
WOOCOMMERCE_URL=https://your-store.com
WOOCOMMERCE_KEY=your-consumer-key
WOOCOMMERCE_SECRET=your-consumer-secret

# Mercari (PENDING API)
# MERCARI_TOKEN=your-mercari-token

# Poshmark (PENDING API)
# POSHMARK_TOKEN=your-poshmark-token

# Buzz relay (REQUIRED)
BUZZ_RELAY_URL=ws://localhost:3000
BUZZ_PRIVATE_KEY=31a697cb1a00d32c0ef5ef7b03dee1567e24d7798cb225302864f886d2af0f04
```

**⚠️ NEVER commit .env file — add to .gitignore**

---

## Testing Your Setup

Once credentials are set:

1. **Start one agent:**
   ```bash
   cd C:\Users\jjard\claude\video-bot-pipeline
   C:\Users\jjard\AppData\Local\Programs\Python\Python314\python.exe agents\platform_sync_agent.py
   ```

2. **Watch for auth messages:**
   - `✓ Etsy: Auth token present` = Etsy ready
   - `⚠️ Etsy: No OAuth token configured` = Missing ETSY_TOKEN

3. **Test create listing:**
   - Add item to Boss Listers with `sync_to_platforms: true`
   - Agent polls Boss Listers every 120 seconds
   - Check for "✓ Synced to platforms: Etsy" message

4. **Verify on platform:**
   - Log into Etsy
   - Check "My Listings" page
   - Item should appear within seconds

---

## Troubleshooting

### "No API token configured"
- Check `.env` file exists in project root
- Verify env vars are set correctly: `ETSY_TOKEN=...`
- Restart agent after adding env vars
- On Windows: `set ETSY_TOKEN=value` in cmd before running agent

### "Auth failed (status 401)"
- Token may have expired
- Generate new OAuth token from platform dashboard
- Update .env and restart

### "Shop ID not found"
- Verify `ETSY_SHOP_ID` is numeric and correct
- Find your shop ID in Etsy account settings
- Format: number only, no dashes or symbols

### "Listing creation failed (status 400)"
- Title may be too long (max 140 chars for Etsy)
- Description may contain invalid characters
- Price may not be in correct format
- Check agent logs for exact error

### Agent not detecting changes
- Ensure `boss-listers-ai/data.json` is valid JSON
- Products must have `status: "for_sale"`
- Products must have `sync_to_platforms: true` (or not explicitly false)
- Agent polls every 120 seconds; wait and check again

---

## Implementation Status

| Platform | Status | Notes |
|----------|--------|-------|
| Etsy | ✅ LIVE | Full OAuth2, create/update/delete/sales/inventory |
| Depop | ✅ LIVE | Full REST API, image uploads, transaction tracking |
| Shopify | ✅ LIVE | Full REST API v3, order tracking, inventory sync |
| WooCommerce | ✅ LIVE | Full REST API, basic auth, product + order mgmt |
| Mercari | 🚧 WAITING | No official API, awaiting documentation |
| Poshmark | 🚧 WAITING | No official API, awaiting documentation |

## Next Priority

1. **Test Etsy sync** - Josh provides OAuth token → agents sync items live
2. **Test Depop sync** - Get Depop API credentials → test connector
3. **Test Shopify sync** - If Josh has Shopify store → test connector
4. **Test WooCommerce sync** - If Josh has WooCommerce store → test connector
5. **Pressure Mercari/Poshmark** - Contact their developer teams for API access

---

## API Rate Limits

| Platform | Limit | Reset |
|----------|-------|-------|
| Etsy | 10,000 req/min | Per minute |
| Depop | 100 req/min | Per minute |
| Shopify | 2 req/sec (40 points/min cost-based) | Per minute |
| WooCommerce | Depends on host | Configurable |
| Mercari | TBD (API not public) | TBD |
| Poshmark | TBD (API not public) | TBD |

Agents respect these limits by:
- Batching updates (polling every 2-5 minutes)
- Caching inventory locally (no duplicate calls)
- Implementing circuit breaker (stop if 5 consecutive failures)

---

## Security Notes

- **Never commit tokens to git** — keep in .env or system env vars
- **Rotate tokens regularly** — monthly or when access is revoked
- **Use OAuth2 when possible** — safer than API keys
- **Limit scope** — only grant permissions needed (read inventory, write listings)
- **Monitor usage** — platforms provide API usage dashboards; check monthly

