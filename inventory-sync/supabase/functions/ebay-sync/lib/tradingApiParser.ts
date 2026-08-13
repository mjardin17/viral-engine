// XML parser for eBay Trading API GetMyeBaySelling responses.
// Handles conversion from XML to structured inventory items.
// Uses regex-based parsing for Deno Edge Function compatibility.

import type { EbayInventoryItem } from "./types.ts";

interface ParsedResponse {
  ack: string;
  totalPages: number;
  totalEntries: number;
  currentPage: number;
  items: EbayInventoryItem[];
  errors: Array<{ code: string; message: string }>;
}

/** Extract text value from XML tag. */
function extractTag(xml: string, tagName: string): string | null {
  const regex = new RegExp(`<${tagName}[^>]*>([^<]*)</${tagName}>`, "i");
  const match = xml.match(regex);
  return match ? match[1] : null;
}

/** Extract all Item blocks from XML. */
function extractItems(xml: string): string[] {
  const itemRegex = /<Item[^>]*>[\s\S]*?<\/Item>/gi;
  const matches = xml.match(itemRegex) || [];
  return matches;
}

/** Parse a single item block (XML string). */
function parseItem(itemXml: string): EbayInventoryItem {
  const getText = (tagName: string): string | null => extractTag(itemXml, tagName);
  const getNum = (tagName: string): number | null => {
    const val = getText(tagName);
    return val ? parseInt(val, 10) : null;
  };

  const itemId = getText("ItemID");
  if (!itemId) throw new Error("ItemID missing from response");

  const quantityAvailable = getNum("QuantityAvailable") ?? 0;
  const quantitySold = getNum("QuantitySold") ?? 0;
  const quantity = getNum("Quantity") ?? 0;

  const price = getText("CurrentPrice");

  return {
    ebayItemId: itemId,
    sku: getText("SKU"),
    title: getText("Title") || "Unknown",
    listingType: getText("ListingType"),
    price: price ? parseFloat(price) : null,
    currency: getText("Currency"),
    quantityListed: quantity,
    quantityAvailable,
    quantitySold,
    imageUrl: getText("PictureURL"),
    watchCount: getNum("WatchCount"),
    bidCount: getNum("BidCount"),
    startTime: getText("ListingDuration"),
    endTime: getText("EndTime"),
    shippingType: getText("ShippingType"),
    shippingCost: null,
    paymentProfileId: getText("PaymentProfileID"),
    returnProfileId: getText("ReturnProfileID"),
    shippingProfileId: getText("ShippingProfileID"),
    sourcePlatform: "ebay",
    sourceEnvironment: "sandbox",
    lastSyncedAt: new Date().toISOString(),
  };
}

/** Parse GetMyeBaySelling response. */
export function parseGetMyeBaySellingResponse(xmlString: string): ParsedResponse {
  const ack = extractTag(xmlString, "Ack") || "Unknown";
  const totalPages = parseInt(extractTag(xmlString, "TotalNumberOfPages") || "0", 10);
  const totalEntries = parseInt(extractTag(xmlString, "TotalNumberOfEntries") || "0", 10);
  const currentPage = parseInt(extractTag(xmlString, "PageNumber") || "1", 10);

  const items: EbayInventoryItem[] = [];
  const itemXmlBlocks = extractItems(xmlString);

  for (const itemXml of itemXmlBlocks) {
    try {
      items.push(parseItem(itemXml));
    } catch (itemError) {
      console.error("Failed to parse item:", itemError);
      // Continue parsing other items
    }
  }

  // Parse errors if Ack indicates failure
  const errors: Array<{ code: string; message: string }> = [];
  const errorRegex = /<Errors[^>]*>[\s\S]*?<\/Errors>/gi;
  const errorBlocks = xmlString.match(errorRegex) || [];
  for (const errorXml of errorBlocks) {
    const code = extractTag(errorXml, "ErrorCode") || "Unknown";
    const message =
      extractTag(errorXml, "LongMessage") ||
      extractTag(errorXml, "ShortMessage") ||
      "Unknown error";
    errors.push({ code, message });
  }

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
