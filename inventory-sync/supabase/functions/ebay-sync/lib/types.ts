// Shared types for the ebay-sync Edge Function.
// Mirrors inventory-sync/supabase/migrations/0001_init_inventory.sql —
// keep both in sync when the schema changes.

export interface ProductRow {
  id?: string;
  sku: string;
  title: string;
  description: string | null;
  price: number;
  quantity: number;
  image_url: string | null;
  condition: string | null;
  status: "active" | "ended" | "draft" | "out_of_stock";
  source: "ebay" | "manual";
  ebay_listing_id: string | null;
  ebay_category_id: string | null;
  last_ebay_price: number | null;
  last_ebay_quantity: number | null;
  synced_at: string;
}

export interface SyncConflict {
  sku: string;
  ebayListingId: string | null;
  reason: string;
  details?: unknown;
}

export interface SyncError {
  stage: "auth" | "fetch_listings" | "upsert" | "unexpected";
  message: string;
  sku?: string;
  ebayItemId?: string;
}

export interface SyncRunResult {
  status: "success" | "partial" | "failed";
  itemsSeen: number;
  itemsUpserted: number;
  conflicts: SyncConflict[];
  errors: SyncError[];
}

// --- eBay Trading API GetMyeBaySelling response (item from active listings) ---

export interface EbayInventoryItem {
  ebayItemId: string;
  sku: string | null;
  title: string;
  listingType: string | null;
  price: number | null;
  currency: string | null;
  quantityListed: number | null;
  quantityAvailable: number | null;
  quantitySold: number | null;
  imageUrl: string | null;
  watchCount: number | null;
  bidCount: number | null;
  startTime: string | null;
  endTime: string | null;
  shippingType: string | null;
  shippingCost: number | null;
  paymentProfileId: string | null;
  returnProfileId: string | null;
  shippingProfileId: string | null;
  sourcePlatform: "ebay";
  sourceEnvironment: "sandbox" | "production";
  lastSyncedAt: string;
}
