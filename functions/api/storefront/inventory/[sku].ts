// GET /api/storefront/inventory/:sku — live quantity/status for one SKU.
// Short 60s cache: this is the endpoint checkout-routing uses to avoid
// sending buyers to sold-out items.

import {
  jsonResponse,
  STOREFRONT_VIEW,
  supabaseRest,
  withEdgeCache,
  type StorefrontEnv,
} from "../../../_lib/supabase";

const CACHE_SECONDS = 60;

export const onRequestGet: PagesFunction<StorefrontEnv> = async (context) =>
  withEdgeCache(context.request, async () => {
    const sku = String(context.params.sku ?? "");
    if (!/^[\w.-]{1,80}$/.test(sku)) {
      return jsonResponse({ error: "Invalid sku" }, 400, 0);
    }

    const upstream = await supabaseRest(
      context.env,
      `${STOREFRONT_VIEW}?select=sku,quantity,status,price&sku=eq.${encodeURIComponent(sku)}&limit=1`,
    );
    if (!upstream.ok) {
      return jsonResponse({ error: "Failed to load inventory" }, 502, 0);
    }
    const rows = (await upstream.json()) as unknown[];
    if (rows.length === 0) {
      return jsonResponse({ error: "Not found" }, 404, 60);
    }
    return jsonResponse({ inventory: rows[0] }, 200, CACHE_SECONDS);
  });
