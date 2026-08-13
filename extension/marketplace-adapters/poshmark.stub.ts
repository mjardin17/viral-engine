// Poshmark adapter — STUB. Structure only; selectors and flows are
// intentionally unimplemented until Poshmark integration is scheduled.

import type { ListingDraft, ListingResult, MarketplaceAdapter } from "../types/adapter";

export const poshmarkAdapter: MarketplaceAdapter = {
  marketplace: "poshmark",

  detectSupportedPage(url: URL): boolean {
    return url.hostname === "poshmark.com" && url.pathname.startsWith("/create-listing");
  },

  readCurrentListing(): Partial<ListingDraft> | null {
    throw new Error("not_implemented");
  },

  async populateListingForm(_document: Document, _draft: ListingDraft): Promise<void> {
    throw new Error("not_implemented");
  },

  collectListingResult(): ListingResult | null {
    throw new Error("not_implemented");
  },
};
