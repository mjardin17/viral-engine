// Cloudflare Pages Function: GET /api/products
// Serves the live Supabase storefront to the site, cached at the edge for
// 5 minutes. The client overlays this with a Supabase Realtime subscription
// (see index.html) for instant updates in between cache refreshes.
//
// Reads the public-safe `storefront_products` VIEW, never the raw `products`
// table. Migration 0008 revoked `select on public.products from anon` on
// purpose — the raw table carries cost/sync/tenant bookkeeping that must not
// be publicly readable, and the view exposes a deliberately narrow column
// set with `where published = true and status in ('active','out_of_stock')`
// as the actual safety boundary. Querying the table with the anon key now
// returns 42501 and this endpoint would answer 502 for every request.
//
// Env vars (Cloudflare Pages -> Settings -> Environment variables):
//   SUPABASE_URL        e.g. https://YOUR_PROJECT_REF.supabase.co
//   SUPABASE_ANON_KEY   the project's public anon key (safe to expose — the
//                       view's grant + filter are what protect the data)

import {
  jsonResponse,
  STOREFRONT_VIEW,
  supabaseRest,
  withEdgeCache,
  type StorefrontEnv,
} from "../_lib/supabase";

const CACHE_SECONDS = 300;

// Narrower than the view's full column list on purpose: the storefront has
// no use for tenant_id or slug, so they never reach the browser.
const PRODUCT_COLUMNS =
  "sku,title,description,price,quantity,image_url,condition,status,ebay_listing_id,updated_at";

export const onRequestGet: PagesFunction<StorefrontEnv> = async (context) =>
  withEdgeCache(context.request, async () => {
    // No `status=neq.draft` filter here — the view already restricts to
    // published rows with status in ('active','out_of_stock'), which is
    // strictly narrower than the old filter.
    const query =
      `${STOREFRONT_VIEW}?select=${PRODUCT_COLUMNS}&order=updated_at.desc`;

    const upstream = await supabaseRest(context.env, query);
    if (!upstream.ok) {
      return jsonResponse({ error: "Failed to load products" }, 502, 0);
    }

    const products = await upstream.json();
    return jsonResponse(
      { products, cachedAt: new Date().toISOString() },
      200,
      CACHE_SECONDS,
    );
  });
