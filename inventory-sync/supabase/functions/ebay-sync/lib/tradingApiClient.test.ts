// Unit tests for eBay Trading API client.
// Tests XML request building, pagination, error handling.

import { assertEquals } from "https://deno.land/std@0.208.0/assert/mod.ts";
import { parseGetMyeBaySellingResponse, isSuccessAck, isPartialAck } from "./tradingApiParser.ts";

Deno.test("tradingApiParser: parses successful GetMyeBaySelling response", () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<GetMyeBaySellingResponse xmlns="urn:ebay:apis:eBLBaseComponents">
  <Ack>Success</Ack>
  <ActiveList>
    <PaginationResult>
      <TotalNumberOfPages>2</TotalNumberOfPages>
      <TotalNumberOfEntries>150</TotalNumberOfEntries>
      <PageNumber>1</PageNumber>
    </PaginationResult>
    <ItemArray>
      <Item>
        <ItemID>123456789</ItemID>
        <SKU>SKU-001</SKU>
        <Title>Test Item 1</Title>
        <ListingType>FixedPriceItem</ListingType>
        <CurrentPrice>99.99</CurrentPrice>
        <Currency>USD</Currency>
        <Quantity>100</Quantity>
        <SellingStatus>
          <QuantityAvailable>50</QuantityAvailable>
          <QuantitySold>50</QuantitySold>
        </SellingStatus>
        <PictureURL>http://example.com/image.jpg</PictureURL>
        <WatchCount>5</WatchCount>
        <BidCount>0</BidCount>
      </Item>
    </ItemArray>
  </ActiveList>
  <SellingSummary/>
</GetMyeBaySellingResponse>`;

  const parsed = parseGetMyeBaySellingResponse(xml);

  assertEquals(parsed.ack, "Success");
  assertEquals(parsed.totalPages, 2);
  assertEquals(parsed.totalEntries, 150);
  assertEquals(parsed.currentPage, 1);
  assertEquals(parsed.items.length, 1);

  const item = parsed.items[0];
  assertEquals(item.ebayItemId, "123456789");
  assertEquals(item.sku, "SKU-001");
  assertEquals(item.title, "Test Item 1");
  assertEquals(item.price, 99.99);
  assertEquals(item.currency, "USD");
  assertEquals(item.quantityAvailable, 50);
  assertEquals(item.quantitySold, 50);
  assertEquals(item.quantityListed, 100);
});

Deno.test("tradingApiParser: handles missing optional fields", () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<GetMyeBaySellingResponse xmlns="urn:ebay:apis:eBLBaseComponents">
  <Ack>Success</Ack>
  <ActiveList>
    <PaginationResult>
      <TotalNumberOfPages>1</TotalNumberOfPages>
      <TotalNumberOfEntries>1</TotalNumberOfEntries>
      <PageNumber>1</PageNumber>
    </PaginationResult>
    <ItemArray>
      <Item>
        <ItemID>987654321</ItemID>
        <Title>Minimal Item</Title>
        <SellingStatus>
          <QuantityAvailable>0</QuantityAvailable>
          <QuantitySold>0</QuantitySold>
        </SellingStatus>
      </Item>
    </ItemArray>
  </ActiveList>
  <SellingSummary/>
</GetMyeBaySellingResponse>`;

  const parsed = parseGetMyeBaySellingResponse(xml);
  const item = parsed.items[0];

  assertEquals(item.ebayItemId, "987654321");
  assertEquals(item.sku, null); // Optional field missing
  assertEquals(item.price, null);
  assertEquals(item.currency, null);
  assertEquals(item.imageUrl, null);
});

Deno.test("tradingApiParser: detects success ACK", () => {
  assertEquals(isSuccessAck("Success"), true);
  assertEquals(isSuccessAck("PartialSuccess"), false);
  assertEquals(isSuccessAck("Failure"), false);
});

Deno.test("tradingApiParser: detects partial ACK", () => {
  assertEquals(isPartialAck("PartialSuccess"), true);
  assertEquals(isPartialAck("Success"), false);
  assertEquals(isPartialAck("Failure"), false);
});

Deno.test("tradingApiParser: parses error response", () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<GetMyeBaySellingResponse xmlns="urn:ebay:apis:eBLBaseComponents">
  <Ack>Failure</Ack>
  <Errors>
    <ErrorCode>931</ErrorCode>
    <ShortMessage>Invalid Auth Token</ShortMessage>
    <LongMessage>The auth token provided is not valid</LongMessage>
  </Errors>
</GetMyeBaySellingResponse>`;

  const parsed = parseGetMyeBaySellingResponse(xml);

  assertEquals(parsed.ack, "Failure");
  assertEquals(parsed.errors.length, 1);
  assertEquals(parsed.errors[0].code, "931");
  assertEquals(parsed.errors[0].message, "The auth token provided is not valid");
});

Deno.test("tradingApiParser: handles multiple items", () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<GetMyeBaySellingResponse xmlns="urn:ebay:apis:eBLBaseComponents">
  <Ack>Success</Ack>
  <ActiveList>
    <PaginationResult>
      <TotalNumberOfPages>1</TotalNumberOfPages>
      <TotalNumberOfEntries>3</TotalNumberOfEntries>
      <PageNumber>1</PageNumber>
    </PaginationResult>
    <ItemArray>
      <Item>
        <ItemID>111</ItemID>
        <SKU>A</SKU>
        <Title>Item A</Title>
        <CurrentPrice>10.00</CurrentPrice>
        <Quantity>5</Quantity>
        <SellingStatus>
          <QuantityAvailable>3</QuantityAvailable>
          <QuantitySold>2</QuantitySold>
        </SellingStatus>
      </Item>
      <Item>
        <ItemID>222</ItemID>
        <SKU>B</SKU>
        <Title>Item B</Title>
        <CurrentPrice>20.00</CurrentPrice>
        <Quantity>10</Quantity>
        <SellingStatus>
          <QuantityAvailable>8</QuantityAvailable>
          <QuantitySold>2</QuantitySold>
        </SellingStatus>
      </Item>
      <Item>
        <ItemID>333</ItemID>
        <SKU>C</SKU>
        <Title>Item C</Title>
        <CurrentPrice>30.00</CurrentPrice>
        <Quantity>15</Quantity>
        <SellingStatus>
          <QuantityAvailable>12</QuantityAvailable>
          <QuantitySold>3</QuantitySold>
        </SellingStatus>
      </Item>
    </ItemArray>
  </ActiveList>
  <SellingSummary/>
</GetMyeBaySellingResponse>`;

  const parsed = parseGetMyeBaySellingResponse(xml);

  assertEquals(parsed.items.length, 3);
  assertEquals(parsed.items[0].ebayItemId, "111");
  assertEquals(parsed.items[1].ebayItemId, "222");
  assertEquals(parsed.items[2].ebayItemId, "333");
  assertEquals(parsed.items[0].quantityAvailable, 3);
  assertEquals(parsed.items[1].quantityAvailable, 8);
  assertEquals(parsed.items[2].quantityAvailable, 12);
});

// ---------------------------------------------------------------------------
// Pagination regression tests.
//
// These cover the bug where `maxPages` was computed as
// `Math.min(1000, totalPages)` BEFORE the first request (totalPages still 1)
// and stored in a `const`, so the loop ran exactly once and every sync was
// silently capped at the first 100 listings. Nothing caught it because no
// test had ever exercised fetchAllActiveListings — only the parser.
// ---------------------------------------------------------------------------

import { fetchAllActiveListings, type FetchLike } from "./tradingApiClient.ts";

const TEST_CONFIG = {
  appId: "app",
  certId: "cert",
  devId: "dev",
  userToken: "token",
  environment: "sandbox" as const,
};

/** Build a GetMyeBaySelling response for one page of a `totalPages` result. */
function pageResponse(pageNumber: number, totalPages: number): string {
  return `<?xml version="1.0" encoding="UTF-8"?>
<GetMyeBaySellingResponse xmlns="urn:ebay:apis:eBLBaseComponents">
  <Ack>Success</Ack>
  <ActiveList>
    <PaginationResult>
      <TotalNumberOfPages>${totalPages}</TotalNumberOfPages>
      <TotalNumberOfEntries>${totalPages * 100}</TotalNumberOfEntries>
      <PageNumber>${pageNumber}</PageNumber>
    </PaginationResult>
    <ItemArray>
      <Item>
        <ItemID>item-page-${pageNumber}</ItemID>
        <Title>Item on page ${pageNumber}</Title>
        <CurrentPrice>10.00</CurrentPrice>
        <SellingStatus>
          <QuantityAvailable>1</QuantityAvailable>
        </SellingStatus>
      </Item>
    </ItemArray>
  </ActiveList>
</GetMyeBaySellingResponse>`;
}

/** Fake transport that records the PageNumber requested on each call. */
function fakeFetch(totalPages: number, requested: number[]): FetchLike {
  return (_url, init) => {
    const body = String(init.body ?? "");
    const page = parseInt(body.match(/<PageNumber>(\d+)<\/PageNumber>/)?.[1] ?? "0", 10);
    requested.push(page);
    return Promise.resolve({
      ok: true,
      status: 200,
      text: () => Promise.resolve(pageResponse(page, totalPages)),
    });
  };
}

Deno.test("fetchAllActiveListings: fetches EVERY page, not just the first", async () => {
  const requested: number[] = [];
  const items = await fetchAllActiveListings(
    TEST_CONFIG,
    "token",
    fakeFetch(3, requested),
  );

  // The bug produced [1] here and a single item.
  assertEquals(requested, [1, 2, 3]);
  assertEquals(items.length, 3);
  assertEquals(items[0].ebayItemId, "item-page-1");
  assertEquals(items[2].ebayItemId, "item-page-3");
});

Deno.test("fetchAllActiveListings: single-page result makes exactly one request", async () => {
  const requested: number[] = [];
  const items = await fetchAllActiveListings(
    TEST_CONFIG,
    "token",
    fakeFetch(1, requested),
  );

  assertEquals(requested, [1]);
  assertEquals(items.length, 1);
});

Deno.test("fetchAllActiveListings: clamps a runaway TotalNumberOfPages to 1000", async () => {
  const requested: number[] = [];
  const items = await fetchAllActiveListings(
    TEST_CONFIG,
    "token",
    fakeFetch(999999, requested),
  );

  assertEquals(requested.length, 1000);
  assertEquals(items.length, 1000);
});

Deno.test("fetchAllActiveListings: throws on a non-Success Ack instead of returning partial data", async () => {
  const failing: FetchLike = () =>
    Promise.resolve({
      ok: true,
      status: 200,
      text: () =>
        Promise.resolve(`<?xml version="1.0"?>
<GetMyeBaySellingResponse>
  <Ack>Failure</Ack>
  <Errors><ErrorCode>931</ErrorCode><LongMessage>Auth token is invalid</LongMessage></Errors>
</GetMyeBaySellingResponse>`),
    });

  let threw = false;
  try {
    await fetchAllActiveListings(TEST_CONFIG, "token", failing);
  } catch (err) {
    threw = true;
    assertEquals(String(err).includes("Auth token is invalid"), true);
  }
  assertEquals(threw, true);
});
