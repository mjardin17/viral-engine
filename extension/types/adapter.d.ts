// Marketplace adapter contract. Every marketplace the extension assists
// with implements exactly this interface — the core never contains
// marketplace-specific logic.

export interface ListingDraft {
  sku: string;
  title: string;
  description: string;
  price: number;
  quantity: number;
  condition: string | null;
  imageUrls: string[];
}

export interface ListingResult {
  ok: boolean;
  /** Marketplace's listing ID, read from the confirmation page. */
  listingId?: string;
  listingUrl?: string;
  error?: string;
}

export interface MarketplaceAdapter {
  /** e.g. "poshmark" — must match marketplace_accounts.marketplace. */
  readonly marketplace: string;

  /** True when the current tab is a supported page for this adapter. */
  detectSupportedPage(url: URL, document: Document): boolean;

  /** Reads the listing currently shown (for import flows). */
  readCurrentListing(document: Document): Partial<ListingDraft> | null;

  /**
   * Fills the marketplace's listing form from the draft. MUST NOT submit —
   * the user reviews and clicks the marketplace's own submit button.
   */
  populateListingForm(document: Document, draft: ListingDraft): Promise<void>;

  /** Reads the post-submit confirmation to capture the listing ID. */
  collectListingResult(document: Document): ListingResult | null;
}
