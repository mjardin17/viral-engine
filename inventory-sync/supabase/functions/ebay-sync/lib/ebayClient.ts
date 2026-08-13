// Thin client over the eBay Sell Inventory API (inventory items + offers).
// All requests go through withRetry so a single flaky call doesn't fail
// the whole sync run.

import { HttpStatusError, isRetryableHttpError, withRetry } from "./retry.ts";
import type { EbayInventoryItem, EbayOffer, EbayOffersPage } from "./types.ts";

const PAGE_SIZE = 100;

function baseUrl(environment: string): string {
  return environment === "sandbox"
    ? "https://api.sandbox.ebay.com/sell/inventory/v1"
    : "https://api.ebay.com/sell/inventory/v1";
}

async function ebayGet<T>(url: string, accessToken: string): Promise<T> {
  return withRetry(
    async () => {
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Language": "en-US",
        },
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new HttpStatusError(
          response.status,
          `eBay GET ${url} failed (${response.status}): ${detail}`,
        );
      }
      return await response.json() as T;
    },
    { isRetryable: isRetryableHttpError },
  );
}

/** Walks every page of the seller's inventory items. */
export async function fetchAllInventoryItems(
  accessToken: string,
  environment: string,
): Promise<EbayInventoryItem[]> {
  const items: EbayInventoryItem[] = [];
  let offset = 0;

  while (true) {
    const url = `${baseUrl(environment)}/inventory_item?limit=${PAGE_SIZE}&offset=${offset}`;
    const page = await ebayGet<{ inventoryItems?: EbayInventoryItem[]; total?: number }>(
      url,
      accessToken,
    );
    const pageItems = page.inventoryItems ?? [];
    items.push(...pageItems);

    offset += pageItems.length;
    const total = page.total ?? items.length;
    if (pageItems.length === 0 || offset >= total) break;
  }

  return items;
}

/** The active offer for a SKU (an inventory item can have at most one published offer per marketplace). */
export async function fetchOfferForSku(
  accessToken: string,
  environment: string,
  sku: string,
): Promise<EbayOffer | null> {
  const url = `${baseUrl(environment)}/offer?sku=${encodeURIComponent(sku)}`;
  const page = await ebayGet<EbayOffersPage>(url, accessToken);
  const offers = page.offers ?? [];
  return offers.find((offer) => offer.status === "PUBLISHED") ?? offers[0] ?? null;
}
