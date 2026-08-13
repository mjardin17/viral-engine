// Shared helper for the storefront Pages Functions. Underscore-prefixed
// directory = not routed by Cloudflare Pages.
//
// Only the ANON key is ever used here. All queries go through the
// public-safe `storefront_products` view (0003 migration) — sync
// bookkeeping, costs, and credentials are structurally unreachable.

export interface StorefrontEnv {
  SUPABASE_URL: string;
  SUPABASE_ANON_KEY: string;
}

export const STOREFRONT_VIEW = "storefront_products";

export async function supabaseRest(
  env: StorefrontEnv,
  pathAndQuery: string,
): Promise<Response> {
  return fetch(`${env.SUPABASE_URL}/rest/v1/${pathAndQuery}`, {
    headers: {
      apikey: env.SUPABASE_ANON_KEY,
      Authorization: `Bearer ${env.SUPABASE_ANON_KEY}`,
    },
  });
}

export function jsonResponse(
  body: unknown,
  status: number,
  cacheSeconds: number,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": `public, max-age=${cacheSeconds}`,
      "Access-Control-Allow-Origin": "*",
    },
  });
}

export async function withEdgeCache(
  request: Request,
  produce: () => Promise<Response>,
): Promise<Response> {
  const cache = caches.default;
  const cacheKey = new Request(request.url, request);
  const cached = await cache.match(cacheKey);
  if (cached) return cached;
  const response = await produce();
  if (response.ok) {
    await cache.put(cacheKey, response.clone());
  }
  return response;
}
