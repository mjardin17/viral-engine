// GET /api/storefront/products        — all published storefront products
// GET /api/storefront/products?q=zeus — title search (ilike)
// Cached 5 minutes at the edge; clients overlay Supabase Realtime for
// instant updates between refreshes.

import {
  jsonResponse,
  STOREFRONT_VIEW,
  supabaseRest,
  withEdgeCache,
  type StorefrontEnv,
} from "../../_lib/supabase";

const CACHE_SECONDS = 300;

export const onRequestGet: PagesFunction<StorefrontEnv> = async (context) =>
  withEdgeCache(context.request, async () => {
    const q = new URL(context.request.url).searchParams.get("q");
    let query = `${STOREFRONT_VIEW}?select=*&order=updated_at.desc&limit=100`;
    if (q) {
      // PostgREST ilike pattern; strip characters that would break the filter.
      const safe = q.replace(/[%,().*]/g, " ").trim().slice(0, 80);
      if (safe) query += `&title=ilike.*${encodeURIComponent(safe)}*`;
    }

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
