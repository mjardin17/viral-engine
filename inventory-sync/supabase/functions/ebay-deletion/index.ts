// Supabase Edge Function: eBay Marketplace Account Deletion/Closure notifications.
//
// eBay requires every developer to either SUBSCRIBE to or OPT OUT of these
// notifications before the first production API call. Until one of those is
// done, the production keyset stays inactive. This function implements the
// subscribe path.
//
// Two behaviours, both required by eBay:
//   GET  ?challenge_code=XYZ  -> prove we own this endpoint by returning
//                                sha256(challenge_code + verificationToken + endpoint)
//                                as { "challengeResponse": "<hex>" }
//   POST <notification body>  -> acknowledge with 200
//
// Required secrets:
//   EBAY_VERIFICATION_TOKEN      the token you type into the eBay portal.
//                                32-80 chars, letters/digits/underscore/hyphen.
//   EBAY_DELETION_ENDPOINT_URL   this function's own public URL, EXACTLY as
//                                registered with eBay.
//
// ⚠️ DEPLOY WITH `--no-verify-jwt`.
// Supabase Edge Functions require an Authorization JWT by default. eBay sends
// no such header, so a default deploy answers 401 and endpoint validation
// fails with a generic error that looks like a hashing bug. See DEPLOY.md.
//
// ⚠️ The endpoint URL must match byte-for-byte what is registered in the
// portal — including scheme, any trailing slash, and case. A mismatch is the
// single most common cause of "endpoint validation failed", because the hash
// is computed over it. That is why this is an explicit env var and is NOT
// derived from the inbound request URL, which proxies can rewrite.

import { computeChallengeResponse } from "./lib/challenge.ts";

function requireEnv(name: string): string {
  const value = Deno.env.get(name);
  if (!value) throw new Error(`Missing required env var: ${name}`);
  return value;
}

Deno.serve(async (req) => {
  let verificationToken: string;
  let endpointUrl: string;
  try {
    verificationToken = requireEnv("EBAY_VERIFICATION_TOKEN");
    endpointUrl = requireEnv("EBAY_DELETION_ENDPOINT_URL");
  } catch (configError) {
    // Loud, not silent — a misconfigured endpoint must not look healthy.
    console.error("ebay-deletion: configuration error:", String(configError));
    return new Response(
      JSON.stringify({ error: "Endpoint is not configured" }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  }

  if (req.method === "GET") {
    const challengeCode = new URL(req.url).searchParams.get("challenge_code");
    if (!challengeCode) {
      return new Response(
        JSON.stringify({ error: "Missing challenge_code" }),
        { status: 400, headers: { "Content-Type": "application/json" } },
      );
    }

    const challengeResponse = await computeChallengeResponse(
      challengeCode,
      verificationToken,
      endpointUrl,
    );

    return new Response(JSON.stringify({ challengeResponse }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (req.method === "POST") {
    // eBay is telling us a user closed their account and any data we hold
    // about them must be deleted.
    //
    // Today this system stores only Josh's OWN listings (products.source =
    // 'ebay', synced from his seller account) — no other eBay user's personal
    // data is persisted anywhere. So there is nothing to purge, and this
    // handler deliberately does NOT pretend to delete anything.
    //
    // If that ever changes — storing buyer names, addresses, or messages (note
    // the `buyer` field on the Sale type in lib/platform_connectors.py) — the
    // purge belongs HERE, and leaving it unimplemented would become a real
    // compliance failure rather than a no-op.
    let username = "unknown";
    let userId = "unknown";
    try {
      const body = await req.json();
      username = body?.notification?.data?.username ?? "unknown";
      userId = body?.notification?.data?.userId ?? "unknown";
    } catch {
      // eBay also sends test pings without a parseable body; still ack.
    }

    console.log(
      `ebay-deletion: account closure received (username=${username}, userId=${userId}); no stored personal data for this user`,
    );

    return new Response(null, { status: 200 });
  }

  return new Response(
    JSON.stringify({ error: "Method not allowed" }),
    { status: 405, headers: { "Content-Type": "application/json" } },
  );
});
