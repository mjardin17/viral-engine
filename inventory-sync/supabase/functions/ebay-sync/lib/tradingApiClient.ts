// eBay Trading API client for GetMyeBaySelling.
// Constructs XML requests and handles pagination.

import { parseGetMyeBaySellingResponse, isSuccessAck } from "./tradingApiParser.ts";
import { HttpStatusError, isRetryableHttpError, withRetry } from "./retry.ts";
import type { EbayInventoryItem } from "./types.ts";

interface TradingApiConfig {
  appId: string;
  certId: string;
  devId: string;
  userToken: string;
  environment: "sandbox" | "production";
}

function baseUrl(environment: "sandbox" | "production"): string {
  return environment === "sandbox"
    ? "https://api.sandbox.ebay.com/ws/api.dll"
    : "https://api.ebay.com/ws/api.dll";
}

/** Build GetMyeBaySelling XML request. */
function buildGetMyeBaySellingRequest(pageNumber: number): string {
  return `<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>REPLACE_TOKEN</eBayAuthToken>
  </RequesterCredentials>
  <ActiveList>
    <Include>true</Include>
    <Pagination>
      <EntriesPerPage>100</EntriesPerPage>
      <PageNumber>${pageNumber}</PageNumber>
    </Pagination>
  </ActiveList>
  <SellingSummary>
    <Include>true</Include>
  </SellingSummary>
</GetMyeBaySellingRequest>`;
}

/**
 * Minimal shape of `fetch` that this client actually uses. Declared so tests
 * can inject a fake transport without constructing real Response objects;
 * the global `fetch` satisfies it structurally.
 */
export type FetchLike = (
  url: string,
  init: RequestInit,
) => Promise<{ ok: boolean; status: number; text: () => Promise<string> }>;

/** Make a Trading API call. */
async function tradingApiCall(
  xml: string,
  config: TradingApiConfig,
  userToken: string,
  fetchImpl: FetchLike,
): Promise<string> {
  const xmlWithToken = xml.replace("REPLACE_TOKEN", userToken);

  return withRetry(
    async () => {
      const response = await fetchImpl(baseUrl(config.environment), {
        method: "POST",
        headers: {
          "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
          "X-EBAY-API-CERT-ID": config.certId,
          "X-EBAY-API-APP-ID": config.appId,
          "X-EBAY-API-COMPATIBILITY-LEVEL": "1335",
          "X-EBAY-API-DEV-ID": config.devId,
          "X-EBAY-API-SITEID": "0",
          "Content-Type": "text/xml",
        },
        body: xmlWithToken,
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new HttpStatusError(
          response.status,
          `eBay Trading API call failed (${response.status}): ${detail}`,
        );
      }

      return await response.text();
    },
    { isRetryable: isRetryableHttpError },
  );
}

/** Hard ceiling on pages fetched, so a bad TotalNumberOfPages can't loop forever. */
const MAX_PAGES = 1000;

/**
 * Fetch all active listings with pagination.
 *
 * The page cap MUST be recomputed after each response. The previous version
 * did `const maxPages = Math.min(1000, totalPages)` before the first request,
 * while totalPages was still its initial 1 — and being a `const`, it never
 * updated. The loop therefore ran exactly once no matter what eBay reported,
 * silently capping every sync at the first 100 listings.
 */
export async function fetchAllActiveListings(
  config: TradingApiConfig,
  userToken: string,
  fetchImpl: FetchLike = fetch,
): Promise<EbayInventoryItem[]> {
  const items: EbayInventoryItem[] = [];
  let pageNumber = 1;
  let totalPages = 1;

  do {
    const xml = buildGetMyeBaySellingRequest(pageNumber);
    const responseXml = await tradingApiCall(xml, config, userToken, fetchImpl);
    const parsed = parseGetMyeBaySellingResponse(responseXml);

    if (!isSuccessAck(parsed.ack)) {
      throw new Error(`GetMyeBaySelling returned ${parsed.ack}: ${parsed.errors.map((e) => e.message).join(", ")}`);
    }

    items.push(...parsed.items);
    // Re-read the real page count from each response, clamped to the ceiling.
    totalPages = Math.min(parsed.totalPages, MAX_PAGES);
    pageNumber++;
  } while (pageNumber <= totalPages);

  return items;
}
