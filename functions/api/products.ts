// Cloudflare Pages Function: GET /api/products
// Serves the live Supabase `products` table to the storefront, cached
// at the edge for 5 minutes. The client overlays this with a Supabase
// Realtime subscription (see index.html) for instant updates in between
// cache refreshes.
//
// Env vars (Cloudflare Pages -> Settings -> Environment variables):
//   SUPABASE_URL        e.g. https://YOUR_PROJECT_REF.supabase.co
//   SUPABASE_ANON_KEY    the project's public anon key (safe to expose —
//                         RLS on `products` only grants public SELECT)

export interface Env {
  SUPABASE_URL: string;
  SUPABASE_ANON_KEY: string;
}

const CACHE_TTL_SECONDS = 300;
const PRODUCT_COLUMNS =
  "sku,title,description,price,quantity,image_url,condition,status,ebay_listing_id,updated_at";

export const onRequestGet: PagesFunction<Env> = async (context) => {
  const cache = caches.default;
  const cacheKey = new Request(context.request.url, context.request);

  const cached = await cache.match(cacheKey);
  if (cached) return cached;

  const restUrl =
    `${context.env.SUPABASE_URL}/rest/v1/products` +
    `?select=${PRODUCT_COLUMNS}&status=neq.draft&order=updated_at.desc`;

  const upstream = await fetch(restUrl, {
    headers: {
      apikey: context.env.SUPABASE_ANON_KEY,
      Authorization: `Bearer ${context.env.SUPABASE_ANON_KEY}`,
    },
  });

  if (!upstream.ok) {
    return new Response(
      JSON.stringify({ error: "Failed to load products" }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  const products = await upstream.json();
  const response = new Response(
    JSON.stringify({ products, cachedAt: new Date().toISOString() }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": `public, max-age=${CACHE_TTL_SECONDS}`,
        "Access-Control-Allow-Origin": "*",
      },
    },
  );

  context.waitUntil(cache.put(cacheKey, response.clone()));
  return response;
};
