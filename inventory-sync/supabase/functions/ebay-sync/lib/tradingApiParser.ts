// XML parser for eBay Trading API GetMyeBaySelling responses.
// Handles conversion from XML to structured inventory items.

import type { EbayInventoryItem } from "./types.ts";

interface ParsedResponse {
  ack: string;
  totalPages: number;
  totalEntries: number;
  currentPage: number;
  items: EbayInventoryItem[];
  errors: Array<{ code: string; message: string }>;
}

/** Parse XML string into a DOM (basic Deno approach). */
function parseXml(xmlString: string): Document {
  // Deno's DOMParser is available in the runtime
  const parser = new DOMParser();
  const doc = parser.parseFromString(xmlString, "application/xml");
  if (!doc) throw new Error("Failed to parse XML response");
  return doc;
}

/** Extract text content from first matching element. */
function getTextContent(doc: Document, path: string): string | null {
  const element = doc.querySelector(path);
  return element ? element.textContent || null : null;
}

/** Extract all matching elements. */
function getElements(doc: Document, path: string): Element[] {
  return Array.from(doc.querySelectorAll(path));
}

/** Parse a single item element. */
function parseItem(itemElement: Element): EbayInventoryItem {
  const getText = (selector: string): string | null => {
    const el = itemElement.querySelector(selector);
    return el ? el.textContent || null : null;
  };

  const getNum = (selector: string): number | null => {
    const val = getText(selector);
    return val ? parseInt(val, 10) : null;
  };

  const itemId = getText("ItemID");
  if (!itemId) throw new Error("ItemID missing from response");

  const quantityAvailable = getNum("SellingStatus > QuantityAvailable") ?? 0;
  const quantitySold = getNum("SellingStatus > QuantitySold") ?? 0;
  const quantity = getNum("Quantity") ?? 0;

  return {
    ebayItemId: itemId,
    sku: getText("SKU"),
    title: getText("Title") || "Unknown",
    listingType: getText("ListingType"),
    price: getText("CurrentPrice") ? parseFloat(getText("CurrentPrice") || "0") : null,
    currency: getText("Currency"),
    quantityListed: quantity,
    quantityAvailable,
    quantitySold,
    imageUrl: getText("PictureURL"),
    watchCount: getNum("WatchCount"),
    bidCount: getNum("BidCount"),
    startTime: getText("ListingDuration"),
    endTime: getText("SellingStatus > EndTime"),
    shippingType: getText("ShippingDetails > ShippingType"),
    shippingCost: getText("ShippingDetails > ShippingServiceOptions > ShippingServiceCost")
      ? parseFloat(getText("ShippingDetails > ShippingServiceOptions > ShippingServiceCost") || "0")
      : null,
    paymentProfileId: getText("PaymentProfile > PaymentProfileID"),
    returnProfileId: getText("ReturnProfile > ReturnProfileID"),
    shippingProfileId: getText("ShippingProfile > ShippingProfileID"),
    sourcePlatform: "ebay",
    sourceEnvironment: "sandbox",
    lastSyncedAt: new Date().toISOString(),
  };
}

/** Parse GetMyeBaySelling response. */
export function parseGetMyeBaySellingResponse(xmlString: string): ParsedResponse {
  const doc = parseXml(xmlString);

  const ack = getTextContent(doc, "Ack") || "Unknown";
  const totalPages = parseInt(getTextContent(doc, "ActiveList > PaginationResult > TotalNumberOfPages") || "0", 10);
  const totalEntries = parseInt(getTextContent(doc, "ActiveList > PaginationResult > TotalNumberOfEntries") || "0", 10);
  const currentPage = parseInt(getTextContent(doc, "ActiveList > PaginationResult > PageNumber") || "1", 10);

  const items: EbayInventoryItem[] = [];
  const itemElements = getElements(doc, "ActiveList > ItemArray > Item");

  for (const itemEl of itemElements) {
    try {
      items.push(parseItem(itemEl));
    } catch (itemError) {
      console.error("Failed to parse item:", itemError);
      // Continue parsing other items
    }
  }

  // Parse errors if Ack indicates failure
  const errorElements = getElements(doc, "Errors");
  const errors = errorElements.map((errEl) => ({
    code: errEl.querySelector("ErrorCode")?.textContent || "Unknown",
    message: errEl.querySelector("LongMessage")?.textContent || errEl.querySelector("ShortMessage")?.textContent || "Unknown error",
  }));

  return { ack, totalPages, totalEntries, currentPage, items, errors };
}

/** Check if response indicates success. */
export function isSuccessAck(ack: string): boolean {
  return ack === "Success";
}

/** Check if response indicates partial success. */
export function isPartialAck(ack: string): boolean {
  return ack === "PartialSuccess";
}
