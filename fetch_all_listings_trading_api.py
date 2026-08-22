#!/usr/bin/env python3
"""Fetch ALL listings via eBay Trading API (GetMyeBaySelling)"""

import os
import requests
from dotenv import load_dotenv
from lib.supabase_client import get_supabase_client
from datetime import datetime

load_dotenv()

# Trading API uses X-EBAY-API-IAF-TOKEN header with Auth'n'Auth user token
user_token = os.getenv("EBAY_AUTH_TOKEN") or os.getenv("EBAY_USER_TOKEN")
if not user_token:
    print("ERROR: EBAY_AUTH_TOKEN or EBAY_USER_TOKEN not set in .env")
    print("Need Auth'n'Auth user token from eBay Developer Portal")
    exit(1)

base_url = "https://api.ebay.com/ws/api.dll"

headers = {
    "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
    "X-EBAY-API-REQUEST-ENCODING": "XML",
    "X-EBAY-API-RESPONSE-ENCODING": "XML",
    "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
    "X-EBAY-API-SITEID": "0",
    "X-EBAY-API-IAF-TOKEN": user_token,
    "Content-Type": "text/xml",
}

# XML request for active listings only
body = """<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{token}</eBayAuthToken>
    </RequesterCredentials>
    <ActiveList>
        <Pagination>
            <EntriesPerPage>100</EntriesPerPage>
            <PageNumber>1</PageNumber>
        </Pagination>
    </ActiveList>
</GetMyeBaySellingRequest>""".format(token=user_token)

all_listings = []
page = 1

print("Fetching ALL active listings via Trading API...")

while True:
    # Update page number in XML body
    body_with_page = body.replace(
        "<PageNumber>1</PageNumber>",
        f"<PageNumber>{page}</PageNumber>"
    )

    response = requests.post(base_url, data=body_with_page.encode(), headers=headers)

    if response.status_code != 200:
        print(f"ERROR {response.status_code}: {response.text[:200]}")
        break

    # Simple XML parsing to count items
    text = response.text
    if "<Ack>Failure</Ack>" in text:
        print(f"eBay returned error: {text[text.find('<LongMessage>'):text.find('</LongMessage>')+len('</LongMessage>')]}")
        break

    # Count <Item> tags in response
    item_count = text.count("<Item>")
    if item_count == 0:
        break

    all_listings.append(f"Page {page}: {item_count} items")
    print(f"  Page {page}: {item_count} items")

    # Stop if less than 100 items (means we're on the last page)
    if item_count < 100:
        break

    page += 1

total = sum(int(line.split(": ")[1].split()[0]) for line in all_listings)
print(f"\n✓ Total listings: {total}")
for line in all_listings:
    print(f"  {line}")
