// eBay marketplace-account-deletion challenge hashing.
//
// Kept in its own module so it can be unit-tested without importing
// index.ts, which calls Deno.serve() at module scope and would bind a port.

/**
 * Compute eBay's expected challenge response.
 *
 * The concatenation order is fixed by eBay and is NOT interchangeable:
 * challengeCode, then verificationToken, then endpoint. Getting the order
 * wrong produces a valid-looking 64-char hex string that fails validation
 * with a generic error — which is why the order is asserted in the tests.
 */
export async function computeChallengeResponse(
  challengeCode: string,
  verificationToken: string,
  endpoint: string,
): Promise<string> {
  const payload = new TextEncoder().encode(
    challengeCode + verificationToken + endpoint,
  );
  const digest = await crypto.subtle.digest("SHA-256", payload);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
