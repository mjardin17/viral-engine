// Tests for the eBay account-deletion challenge hash.
//
// Anchored to a published SHA-256 vector rather than to this implementation's
// own output — a test that just records whatever the code returns would pass
// even if the concatenation order were wrong, which is the exact failure mode
// that makes eBay endpoint validation fail with an unhelpful error.

import { assertEquals, assertNotEquals } from "https://deno.land/std@0.208.0/assert/mod.ts";
import { computeChallengeResponse } from "./challenge.ts";

// Known vector: SHA-256("abc")
const SHA256_ABC =
  "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";

Deno.test("computeChallengeResponse: matches the published SHA-256 vector for 'abc'", async () => {
  // challengeCode="a", verificationToken="b", endpoint="c" -> hashes "abc".
  // This simultaneously pins the algorithm AND the concatenation order.
  assertEquals(await computeChallengeResponse("a", "b", "c"), SHA256_ABC);
});

Deno.test("computeChallengeResponse: order is significant (wrong order must not match)", async () => {
  const correct = await computeChallengeResponse("a", "b", "c");
  const swapped = await computeChallengeResponse("b", "a", "c");
  const reversed = await computeChallengeResponse("c", "b", "a");

  assertNotEquals(correct, swapped);
  assertNotEquals(correct, reversed);
});

Deno.test("computeChallengeResponse: returns lowercase 64-char hex for realistic input", async () => {
  const hash = await computeChallengeResponse(
    "71745723-d031-455c-bfa5-f90d11b4f20a",
    "empire-os-verification-token-0123456789",
    "https://irslzufsqjveyibkfjtz.supabase.co/functions/v1/ebay-deletion",
  );

  assertEquals(hash.length, 64);
  assertEquals(/^[0-9a-f]{64}$/.test(hash), true);
});

Deno.test("computeChallengeResponse: a trailing slash on the endpoint changes the hash", async () => {
  // The most common real-world validation failure: the registered URL and the
  // hashed URL differ by a trailing slash. Documenting it as a test so the
  // next person sees it before spending an afternoon on it.
  const withoutSlash = await computeChallengeResponse(
    "code",
    "token",
    "https://example.com/functions/v1/ebay-deletion",
  );
  const withSlash = await computeChallengeResponse(
    "code",
    "token",
    "https://example.com/functions/v1/ebay-deletion/",
  );

  assertNotEquals(withoutSlash, withSlash);
});
