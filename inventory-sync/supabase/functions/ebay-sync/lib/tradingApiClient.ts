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

/** Make a Trading API call. */
async function tradingApiCall(
  xml: string,
  config: TradingApiConfig,
  userToken: string,
): Promise<string> {
  const xmlWithToken = xml.replace("REPLACE_TOKEN", userToken);

  return withRetry(
    async () => {
      const response = await fetch(baseUrl(config.environment), {
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

/** Fetch all active listings with pagination. */
export async function fetchAllActiveListings(
  config: TradingApiConfig,
  userToken: string,
): Promise<EbayInventoryItem[]> {
  const items: EbayInventoryItem[] = [];
  let pageNumber = 1;
  let totalPages = 1;

  // Pagination safety: never exceed 1000 pages
  const maxPages = Math.min(1000, totalPages);

  while (pageNumber <= maxPages) {
    const xml = buildGetMyeBaySellingRequest(pageNumber);
    const responseXml = await tradingApiCall(xml, config, userToken);
    const parsed = parseGetMyeBaySellingResponse(responseXml);

    if (!isSuccessAck(parsed.ack)) {
      throw new Error(`GetMyeBaySelling returned ${parsed.ack}: ${parsed.errors.map((e) => e.message).join(", ")}`);
    }

    items.push(...parsed.items);
    totalPages = parsed.totalPages;
    pageNumber++;
  }

  return items;
}
