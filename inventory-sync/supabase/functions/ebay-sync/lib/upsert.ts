// Maps an eBay Trading API GetMyeBaySelling item into a `products` row and
// upserts it. Conflicts (e.g. an eBay listing ID that already belongs
// to a different SKU) are reported back rather than thrown, so one bad
// item never aborts the rest of the run.

import type { SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2?dts";
import type { EbayInventoryItem, ProductRow, SyncConflict, SyncError } from "./types.ts";

export function buildProductRow(item: EbayInventoryItem): ProductRow {
  const quantity = item.quantityAvailable ?? 0;
  const price = item.price ?? 0;
  // SKU can be null in the API response; fall back to itemID if needed
  const sku = item.sku ?? item.ebayItemId;

  return {
    sku,
    title: item.title,
    description: null,
    price,
    quantity,
    image_url: item.imageUrl ?? null,
    condition: null,
    status: quantity === 0 ? "out_of_stock" : "active",
    source: "ebay",
    ebay_listing_id: item.ebayItemId,
    ebay_category_id: null,
    last_ebay_price: price,
    last_ebay_quantity: quantity,
    synced_at: item.lastSyncedAt,
  };
}

export interface UpsertOutcome {
  upserted: boolean;
  conflict?: SyncConflict;
  error?: SyncError;
}

export async function upsertProduct(
  supabase: SupabaseClient,
  row: ProductRow,
): Promise<UpsertOutcome> {
  // A listing ID moving to a different SKU means eBay reassigned it
  // (or two SKUs collided) — surface it as a conflict instead of
  // silently stealing the row from its previous SKU.
  if (row.ebay_listing_id) {
    const { data: existingForListing } = await supabase
      .from("products")
      .select("sku")
      .eq("ebay_listing_id", row.ebay_listing_id)
      .neq("sku", row.sku)
      .maybeSingle();

    if (existingForListing) {
      return {
        upserted: false,
        conflict: {
          sku: row.sku,
          ebayListingId: row.ebay_listing_id,
          reason: "ebay_listing_id already belongs to a different SKU",
          details: { existingSku: existingForListing.sku },
        },
      };
    }
  }

  const { error } = await supabase
    .from("products")
    .upsert(row, { onConflict: "sku" });

  if (error) {
    return {
      upserted: false,
      error: { stage: "upsert", message: error.message, sku: row.sku },
    };
  }

  return { upserted: true };
}
