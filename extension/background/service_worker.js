// Boss Listers Assistant — background service worker (SCAFFOLD).
//
// Responsibilities when implemented:
//   * Hold the authenticated Boss Listers session (short-lived signed
//     extension token from the BossLister backend — never marketplace
//     passwords, never provider API keys).
//   * Broker messages between the popup/content scripts and the backend.
//   * Enforce the operation allowlist (marketplace + operation + expiry
//     + nonce validated server-side before any product data is released).
//
// HARD RULES (also enforced by review, see extension/README.md):
//   * No provider API keys or Supabase service-role keys anywhere in the
//     extension. Content scripts receive only the single ListingDraft
//     they need, never tokens.
//   * Never auto-submit forms. Population only; the user clicks submit.
//   * No interaction with CAPTCHAs or MFA prompts — if one appears, stop
//     and surface a "complete this yourself" notice.

const STATE = { connected: false };

chrome.runtime.onInstalled.addListener(() => {
  console.info("[boss-listers] scaffold installed — no functionality yet");
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  // Scaffold: every operation reports not-implemented.
  sendResponse({ ok: false, error: "not_implemented", state: STATE });
  return false;
});
