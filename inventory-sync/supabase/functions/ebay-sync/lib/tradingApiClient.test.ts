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
