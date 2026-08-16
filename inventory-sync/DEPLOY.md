# Deploy — eBay Trading API → Supabase → Website/Boss Listers Live Inventory

Everything here runs on free tiers: Supabase (Edge Functions, pg_cron, pg_net,
Realtime, Postgres), Cloudflare Pages (Functions), and eBay's Developer API
are all free at this scale. No paid services required.

## Architecture recap

```
eBay Trading API GetMyeBaySelling
        │  polled every 15 min by pg_cron
        ▼
Supabase Edge Function (ebay-sync)  ──upsert──▶  public.products (Postgres)
        │                                              │  RLS: public SELECT
        │ writes                                       │  writes: service_role
        ▼                                               or app_metadata.role="boss_lister"
public.sync_logs / public.sync_state                    │
                                                          ├─▶ Cloudflare Pages Function
                                                          │   GET /api/products (5-min edge cache)
                                                          │   → index.html "Shop The Inventory" section
                                                          │
                                                          └─▶ Supabase Realtime subscription
                                                              → index.html live overlay
                                                              → Boss Listers dashboard (Vercel)
```

Deviation from the original brief worth flagging: the brief asked for sync
logging in `DRY_RUN_REPORT.md`, but that file is already owned by the video
pipeline's `dry_run.py` (auto-regenerated on every pipeline dry run) —
reusing it here would clobber unrelated diagnostics. Instead, every sync run
writes a structured row to `public.sync_logs` (queryable, and the correct
place for a stateless Edge Function to log to — it has no filesystem to
write a repo file to at runtime anyway). `inventory-sync/reports/` has a
query to pull that into a markdown snapshot on demand.

**API Choice:** Trading API (GetMyeBaySelling, XML-RPC) was chosen over Sell
Inventory API (REST/JSON) because the specification required access to live
active listings with pagination, full pricing/quantity/status data, and
seller inventory context — all native to Trading API. Trading API also
provides better pagination and handles high-volume sellers more efficiently.

---

## 1. Create the Supabase project

1. [supabase.com](https://supabase.com) → New Project (free tier).
2. Project Settings → API → copy the **Project URL**, **anon public key**,
   and **service_role key**. You'll need all three below.
3. Project Settings → General → copy the **Project ref** (the subdomain in
   your project URL, e.g. `abcdefghijklmnop`).

## 2. Run the schema migrations

Using the Supabase CLI (recommended):

```bash
npx supabase login
npx supabase link --project-ref irslzufsqjveyibkfjtz
npx supabase db push
```

Project confirmed 2026-07-26: **"Boss listers prod" = `irslzufsqjveyibkfjtz`**
(key/ref pair verified live). Do NOT use the other, unused project
(`lgevctbpntndmbwgebwe`). This applies `0001_init_inventory.sql` (schema, RLS,
realtime), `0002_schedule_ebay_sync.sql` (cron — project URL already filled
in), and `0003_commerce_hardening.sql` (marketplace tables, record_sale,
storefront view).

No CLI available? Paste each migration file's contents into the Supabase
Dashboard's SQL Editor and run them in order (0001 then 0002).

## 3. Create the eBay developer app + get a user token

The Trading API needs your application credentials (App ID, Cert ID, Dev ID)
and a **user-scoped token** (it reads your own seller's active listings).

1. [developer.ebay.com](https://developer.ebay.com) → sign in with your eBay
   seller account → **My Account → Application Keys**. Create a keyset for
   **Sandbox** (for testing) and/or **Production** (for live listings).
2. Copy and save the **App ID**, **Cert ID**, and **Dev ID** from both
   keysets (you'll need these later).
3. Under **User Tokens**, generate an Auth Token for your seller account
   (this is the user-scoped token the Trading API needs). Save it somewhere
   safe.
4. (Optional but recommended) Set a **RuName** (OAuth redirect identifier)
   if you plan to implement authenticated third-party app access later.

> **Do NOT run an OAuth consent flow for this.** The Trading API uses an
> Auth'n'Auth **User Token** (step 3), not OAuth. OAuth gives you a
> client id / secret / refresh token — none of which this function reads.
> Three separate setup attempts failed for exactly this reason.

## 3b. Activate the production keyset (marketplace account deletion)

**Production API calls are blocked until this is done.** eBay requires every
developer to either subscribe to or opt out of marketplace account
deletion/closure notifications before the first production call. This is
**self-service — there is no review queue.** Sandbox is unaffected.

Two options:

**Option A — opt out.** In the portal, set *"Not persisting eBay data"* to On,
pick a reason, submit. Only honest if you store no eBay user personal data.
This repo currently stores only your own listings, but note the `buyer` field
on the `Sale` type in `lib/platform_connectors.py` — if that ever gets
populated, Option A stops being true.

**Option B — subscribe (implemented here).** Deploy the `ebay-deletion`
function and register its URL.

```bash
# 1. Pick a verification token: 32-80 chars, letters/digits/underscore/hyphen.
npx supabase secrets set EBAY_VERIFICATION_TOKEN=your_generated_token

# 2. The function's own public URL, EXACTLY as you will register it.
npx supabase secrets set \
  EBAY_DELETION_ENDPOINT_URL=https://YOUR_PROJECT_REF.supabase.co/functions/v1/ebay-deletion

# 3. Deploy. --no-verify-jwt is REQUIRED (see below).
npx supabase functions deploy ebay-deletion --no-verify-jwt
```

Then in the eBay portal → **Alerts & Notifications** → Marketplace Account
Deletion: paste the same URL and the same verification token, and click
**Send Test Notification**.

Two failure modes account for nearly every "endpoint validation failed":

- **Missing `--no-verify-jwt`.** Supabase Edge Functions demand an
  `Authorization` JWT by default. eBay sends none, so the endpoint answers
  **401** and eBay reports a generic validation failure that looks like a
  hashing bug. It isn't.
- **URL mismatch.** The response hash is computed over the endpoint URL, so
  the value in `EBAY_DELETION_ENDPOINT_URL` must match what you registered
  **byte-for-byte** — scheme, case, and trailing slash included. A trailing
  slash on one side and not the other produces a valid-looking 64-char hash
  that fails. (`lib/challenge.test.ts` covers this case explicitly.)

Verify locally before deploying:

```bash
cd supabase/functions/ebay-deletion && deno test --allow-net lib/
```

## 4. Set Edge Function secrets

For **Sandbox** testing:
```bash
npx supabase secrets set \
  EBAY_SANDBOX_APP_ID=your_sandbox_app_id \
  EBAY_SANDBOX_CERT_ID=your_sandbox_cert_id \
  EBAY_SANDBOX_DEV_ID=your_sandbox_dev_id \
  EBAY_SANDBOX_USER_TOKEN=your_sandbox_user_token \
  EBAY_ENVIRONMENT=sandbox \
  SYNC_TRIGGER_SECRET=$(openssl rand -hex 32)
```

For **Production** (after Testing passes):
```bash
npx supabase secrets set \
  EBAY_PRODUCTION_APP_ID=your_production_app_id \
  EBAY_PRODUCTION_CERT_ID=your_production_cert_id \
  EBAY_PRODUCTION_DEV_ID=your_production_dev_id \
  EBAY_PRODUCTION_USER_TOKEN=your_production_user_token \
  EBAY_ENVIRONMENT=production \
  SYNC_TRIGGER_SECRET=$(openssl rand -hex 32)
```

`SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are injected automatically by
Supabase into every Edge Function — you don't set those yourself.

Save the `SYNC_TRIGGER_SECRET` value you just generated; it's needed again
in step 6.

## 5. Deploy the Edge Function

```bash
npx supabase functions deploy ebay-sync
```

Verify it's live:

```bash
curl -i https://irslzufsqjveyibkfjtz.supabase.co/functions/v1/ebay-sync \
  -H "x-sync-trigger-secret: YOUR_SYNC_TRIGGER_SECRET"
```

You should get back a `200` with a JSON summary (`itemsSeen`,
`itemsUpserted`, etc.) and a new row in `public.sync_logs`.

## 6. Wire up pg_cron (the 15-minute schedule)

Dashboard → Project Settings → Vault → add two secrets:

| name | value |
|---|---|
| `sync_service_role_key` | your service_role key from step 1 |
| `sync_trigger_secret` | the same value you set as `SYNC_TRIGGER_SECRET` in step 4 |

If you haven't already applied `0002_schedule_ebay_sync.sql` (step 2), do it
now — it schedules `net.http_post` to hit the function every 15 minutes
using those two Vault secrets. Confirm it's scheduled:

```sql
select * from cron.job where jobname = 'ebay-sync-every-15-min';
```

## 7. Point the website at Supabase

In `index.html`, find `SUPABASE_URL` / `SUPABASE_ANON_KEY` (search the file
— there's only one place to change them) and set them to your project's
values. This is the **anon** key, safe to ship client-side — RLS only grants
it public `SELECT` on `products`.

In your Cloudflare Pages project (the one serving this repo as
jardins-outpost.pages.dev): **Settings → Environment variables**, add:

| name | value |
|---|---|
| `SUPABASE_URL` | `https://irslzufsqjveyibkfjtz.supabase.co` |
| `SUPABASE_ANON_KEY` | your anon key |

This powers `functions/api/products.ts` (`GET /api/products`, 5-min edge
cache). Push to `main` and Cloudflare Pages picks up both the static HTML
change and the new Function automatically — no separate deploy step.

## 8. Point Boss Listers (Vercel) at Supabase

Once `boss-listers-ai/boss-listers-ai/` is generated into a real app (see
its `README.txt`) and deployed to Vercel:

1. `cp .env.example .env` locally and fill in `VITE_SUPABASE_URL` /
   `VITE_SUPABASE_ANON_KEY` for local dev.
2. In the Vercel project → Settings → Environment Variables, add the same
   two keys for Production/Preview.
3. Writes need an authenticated user with `app_metadata.role = "boss_lister"`.
   Create one: Supabase Dashboard → Authentication → Users → Add User, then
   in the SQL Editor:
   ```sql
   update auth.users
   set raw_app_meta_data = raw_app_meta_data || '{"role": "boss_lister"}'::jsonb
   where email = 'you@example.com';
   ```

## 9. Verify end-to-end

- `select * from public.sync_logs order by started_at desc limit 5;` — should
  show a new row every ~15 min with `status = 'success'`.
- `select sku, title, price, quantity, status from public.products;` —
  should match your live eBay listings.
- Load the website, scroll to **Shop The Inventory** — cards should render
  from `/api/products`. Change a price on eBay, wait for the next sync (or
  trigger it manually per step 5), and the card should update without a
  page reload once the Realtime subscription picks it up.

## Rotating / pausing

- Pause the sync without undeploying: `select cron.unschedule('ebay-sync-every-15-min');`
- Rotate the eBay user token: repeat step 3 (generate a new **Auth'n'Auth User
  Token** — NOT an OAuth token), then
  `npx supabase secrets set EBAY_PRODUCTION_USER_TOKEN=new_token`
  (or `EBAY_SANDBOX_USER_TOKEN`, matching `EBAY_ENVIRONMENT`).
  There is no `EBAY_REFRESH_TOKEN` — this function uses the legacy Trading
  API, which has no OAuth refresh flow. Setting OAuth secrets here does
  nothing; the function never reads them.
- Rotate `SYNC_TRIGGER_SECRET`: update both the Edge Function secret (step 4)
  and the Vault secret (step 6) — they must match.
