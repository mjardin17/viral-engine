// Supabase Edge Function: polls the seller's eBay active listings using Trading API,
// upserts them into `public.products`, and records a `sync_logs` row.
// Triggered every 15 minutes by pg_cron (see migrations/0002_schedule_ebay_sync.sql).
//
// Required secrets (set via `supabase secrets set`, see inventory-sync/DEPLOY.md):
//   EBAY_SANDBOX_APP_ID, EBAY_SANDBOX_CERT_ID, EBAY_SANDBOX_DEV_ID, EBAY_SANDBOX_USER_TOKEN (for sandbox testing)
//   EBAY_PRODUCTION_APP_ID, EBAY_PRODUCTION_CERT_ID, EBAY_PRODUCTION_DEV_ID, EBAY_PRODUCTION_USER_TOKEN (for production)
//   EBAY_ENVIRONMENT (set to 'sandbox' or 'production'; defaults to 'production')
//   SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (Supabase injects these automatically)

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { fetchAllActiveListings } from "./lib/tradingApiClient.ts";
import { buildProductRow, upsertProduct } from "./lib/upsert.ts";
import { CircuitBreaker } from "./lib/circuitBreaker.ts";
import { RetryExhaustedError } from "./lib/retry.ts";
import type { SyncConflict, SyncError, SyncRunResult } from "./lib/types.ts";

function requireEnv(name: string): string {
  const value = Deno.env.get(name);
  if (!value) throw new Error(`Missing required env var: ${name}`);
  return value;
}

async function runSync(): Promise<SyncRunResult> {
  const supabase = createClient(
    requireEnv("SUPABASE_URL"),
    requireEnv("SUPABASE_SERVICE_ROLE_KEY"),
  );
  const breaker = new CircuitBreaker(supabase);

  const conflicts: SyncConflict[] = [];
  const errors: SyncError[] = [];
  let itemsSeen = 0;
  let itemsUpserted = 0;

  if (await breaker.isOpen()) {
    return {
      status: "failed",
      itemsSeen: 0,
      itemsUpserted: 0,
      conflicts: [],
      errors: [{ stage: "unexpected", message: "Circuit breaker open — skipping run" }],
    };
  }

  const environment = (Deno.env.get("EBAY_ENVIRONMENT") ?? "production") as "sandbox" | "production";
  const envPrefix = environment === "sandbox" ? "EBAY_SANDBOX" : "EBAY_PRODUCTION";

  const tradingConfig = {
    appId: requireEnv(`${envPrefix}_APP_ID`),
    certId: requireEnv(`${envPrefix}_CERT_ID`),
    devId: requireEnv(`${envPrefix}_DEV_ID`),
    userToken: requireEnv(`${envPrefix}_USER_TOKEN`),
    environment,
  };

  try {
    const items = await fetchAllActiveListings(tradingConfig, tradingConfig.userToken);
    itemsSeen = items.length;

    for (const item of items) {
      try {
        const row = buildProductRow(item);
        const outcome = await upsertProduct(supabase, row);

        if (outcome.upserted) itemsUpserted++;
        if (outcome.conflict) conflicts.push(outcome.conflict);
        if (outcome.error) errors.push(outcome.error);
      } catch (itemError) {
        errors.push({
          stage: "upsert",
          message: itemError instanceof RetryExhaustedError
            ? itemError.message
            : String(itemError),
          ebayItemId: item.ebayItemId,
        });
      }
    }

    await breaker.recordSuccess();
  } catch (fatalError) {
    await breaker.recordFailure();
    errors.push({
      stage: fatalError instanceof RetryExhaustedError && itemsSeen === 0 ? "auth" : "fetch_listings",
      message: String(fatalError),
    });
  }

  const status: SyncRunResult["status"] = errors.length === 0
    ? "success"
    : itemsUpserted > 0
    ? "partial"
    : "failed";

  return { status, itemsSeen, itemsUpserted, conflicts, errors };
}

Deno.serve(async (req) => {
  // pg_cron calls this with a shared-secret header (see 0002 migration) —
  // reject anything else so the function can't be triggered publicly.
  const cronSecret = Deno.env.get("SYNC_TRIGGER_SECRET");
  if (cronSecret && req.headers.get("x-sync-trigger-secret") !== cronSecret) {
    return new Response("Forbidden", { status: 403 });
  }

  const supabase = createClient(
    requireEnv("SUPABASE_URL"),
    requireEnv("SUPABASE_SERVICE_ROLE_KEY"),
  );

  const startedAt = new Date();
  const result = await runSync();
  const finishedAt = new Date();

  await supabase.from("sync_logs").insert({
    started_at: startedAt.toISOString(),
    finished_at: finishedAt.toISOString(),
    status: result.status,
    items_seen: result.itemsSeen,
    items_upserted: result.itemsUpserted,
    conflicts: result.conflicts,
    errors: result.errors,
  });

  return new Response(JSON.stringify(result), {
    status: result.status === "failed" ? 500 : 200,
    headers: { "Content-Type": "application/json" },
  });
});
