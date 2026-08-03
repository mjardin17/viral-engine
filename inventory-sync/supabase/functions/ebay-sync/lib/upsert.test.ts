// Unit tests for buildProductRow mapping.
// Tests conversion from eBay Trading API items to ProductRow.

import { assertEquals, assertStrictEquals } from "https://deno.land/std@0.208.0/assert/mod.ts";
import { buildProductRow } from "./upsert.ts";
import type { EbayInventoryItem } from "./types.ts";

Deno.test("buildProductRow: maps full Trading API response", () => {
  const item: EbayInventoryItem = {
    ebayItemId: "123456789",
    sku: "SKU-001",
    title: "Test Listing",
    listingType: "FixedPriceItem",
    price: 99.99,
    currency: "USD",
    quantityListed: 100,
    quantityAvailable: 50,
    quantitySold: 50,
    imageUrl: "http://example.com/image.jpg",
    watchCount: 5,
    bidCount: 0,
    startTime: "2024-01-01",
    endTime: "2025-01-01",
    shippingType: "Flat",
    shippingCost: 5.00,
    paymentProfileId: "pay-123",
    returnProfileId: "ret-456",
    shippingProfileId: "ship-789",
    sourcePlatform: "ebay",
    sourceEnvironment: "production",
    lastSyncedAt: "2024-01-15T10:00:00Z",
  };

  const row = buildProductRow(item);

  assertEquals(row.sku, "SKU-001");
  assertEquals(row.title, "Test Listing");
  assertEquals(row.price, 99.99);
  assertEquals(row.quantity, 50);
  assertEquals(row.image_url, "http://example.com/image.jpg");
  assertEquals(row.status, "active");
  assertEquals(row.source, "ebay");
  assertEquals(row.ebay_listing_id, "123456789");
  assertEquals(row.last_ebay_price, 99.99);
  assertEquals(row.last_ebay_quantity, 50);
  assertEquals(row.synced_at, "2024-01-15T10:00:00Z");
});

Deno.test("buildProductRow: handles out-of-stock", () => {
  const item: EbayInventoryItem = {
    ebayItemId: "111",
    sku: "SKU-OOS",
    title: "Out of Stock Item",
    listingType: null,
    price: 50.00,
    currency: "USD",
    quantityListed: 10,
    quantityAvailable: 0,
    quantitySold: 10,
    imageUrl: null,
    watchCount: null,
    bidCount: null,
    startTime: null,
    endTime: null,
    shippingType: null,
    shippingCost: null,
    paymentProfileId: null,
    returnProfileId: null,
    shippingProfileId: null,
    sourcePlatform: "ebay",
    sourceEnvironment: "sandbox",
    lastSyncedAt: "2024-01-15T11:00:00Z",
  };

  const row = buildProductRow(item);

  assertEquals(row.quantity, 0);
  assertEquals(row.status, "out_of_stock");
});

Deno.test("buildProductRow: falls back to itemId when SKU is null", () => {
  const item: EbayInventoryItem = {
    ebayItemId: "999",
    sku: null,
    title: "Item Without SKU",
    listingType: null,
    price: 25.00,
    currency: "USD",
    quantityListed: 5,
    quantityAvailable: 3,
    quantitySold: 2,
    imageUrl: null,
    watchCount: null,
    bidCount: null,
    startTime: null,
    endTime: null,
    shippingType: null,
    shippingCost: null,
    paymentProfileId: null,
    returnProfileId: null,
    shippingProfileId: null,
    sourcePlatform: "ebay",
    sourceEnvironment: "production",
    lastSyncedAt: "2024-01-15T12:00:00Z",
  };

  const row = buildProductRow(item);

  // Should use itemId as SKU fallback
  assertEquals(row.sku, "999");
  assertEquals(row.title, "Item Without SKU");
  assertEquals(row.ebay_listing_id, "999");
});

Deno.test("buildProductRow: sets correct defaults", () => {
  const item: EbayInventoryItem = {
    ebayItemId: "555",
    sku: "SKU-DEFAULTS",
    title: "Test",
    listingType: null,
    price: null,
    currency: null,
    quantityListed: null,
    quantityAvailable: null,
    quantitySold: null,
    imageUrl: null,
    watchCount: null,
    bidCount: null,
    startTime: null,
    endTime: null,
    shippingType: null,
    shippingCost: null,
    paymentProfileId: null,
    returnProfileId: null,
    shippingProfileId: null,
    sourcePlatform: "ebay",
    sourceEnvironment: "sandbox",
    lastSyncedAt: "2024-01-15T13:00:00Z",
  };

  const row = buildProductRow(item);

  assertEquals(row.price, 0);
  assertEquals(row.quantity, 0);
  assertEquals(row.status, "out_of_stock");
  assertEquals(row.image_url, null);
  assertEquals(row.condition, null);
  assertEquals(row.description, null);
  assertEquals(row.ebay_category_id, null);
});
