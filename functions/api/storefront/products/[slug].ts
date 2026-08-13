// GET /api/storefront/products/:slug — one published storefront product.
// Cached 5 minutes at the edge.

import {
  jsonResponse,
  STOREFRONT_VIEW,
  supabaseRest,
  withEdgeCache,
  type StorefrontEnv,
} from "../../../_lib/supabase";

const CACHE_SECONDS = 300;

export const onRequestGet: PagesFunction<StorefrontEnv> = async (context) =>
  withEdgeCache(context.request, async () => {
    const slug = String(context.params.slug ?? "");
    if (!/^[a-z0-9-]{1,120}$/.test(slug)) {
      return jsonResponse({ error: "Invalid slug" }, 400, 0);
    }

    const upstream = await supabaseRest(
      context.env,
      `${STOREFRONT_VIEW}?select=*&slug=eq.${encodeURIComponent(slug)}&limit=1`,
    );
    if (!upstream.ok) {
      return jsonResponse({ error: "Failed to load product" }, 502, 0);
    }
    const rows = (await upstream.json()) as unknown[];
    if (rows.length === 0) {
      return jsonResponse({ error: "Not found" }, 404, 60);
    }
    return jsonResponse({ product: rows[0] }, 200, CACHE_SECONDS);
  });
