# Boss Listers Assistant — browser extension (SCAFFOLD, not functional)

Status: **NOT IMPLEMENTED — architecture scaffold only.** Nothing here
lists, updates, or reads anything yet. It exists so future marketplace
adapters land in a structure with the compliance rules already baked in.

## Role in the architecture

Fallback connector ONLY for marketplaces without a usable official API
(e.g. Poshmark, Mercari, Depop). Marketplaces with official APIs (eBay,
Etsy, Shopify, TikTok Shop, Amazon, Walmart) connect server-side through
BossLister's OAuth integrations and never touch this extension.

## Compliance rules (non-negotiable, enforced at review)

1. Operates only while the user is signed into the marketplace themselves.
2. **Fills forms, never submits them** — the user reviews and clicks the
   marketplace's own submit button for every listing.
3. Zero interaction with CAPTCHAs, MFA, or bot-detection. If one appears,
   the extension stops and tells the user to complete it.
4. No marketplace passwords stored, ever.
5. No provider API keys, Supabase service-role keys, or encryption keys in
   the manifest, background, content scripts, or storage.
6. Minimum permissions: `activeTab` + `storage` only; marketplace hosts are
   `optional_host_permissions` granted per-marketplace by the user.
7. Backend auth uses short-lived signed extension tokens (issued by the
   BossLister backend against an authenticated session) with expiry +
   nonce; content scripts receive only the single ListingDraft they need.
8. No browsing capture outside the explicitly supported listing pages.

## Structure

```
extension/
  manifest.json                     MV3, minimal permissions
  background/service_worker.js      session + message broker (stub)
  marketplace-adapters/             one adapter per marketplace (stubs)
  types/adapter.d.ts                the adapter contract
  security/                         token validation (to be implemented)
```

## Next steps (when scheduled)

1. Implement the BossLister backend endpoint that issues extension tokens.
2. Implement `security/token.ts` (verify expiry/nonce, request signing).
3. Implement the first real adapter (Poshmark) against `types/adapter.d.ts`.
4. Add `tests/` with fixture DOM pages per marketplace.
