// Circuit breaker backed by the single-row `sync_state` table. Edge
// Functions are stateless between invocations, so breaker state has to
// live in Postgres rather than in memory.

import type { SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2?dts";

const FAILURE_THRESHOLD = 5;
const OPEN_DURATION_MS = 30 * 60 * 1000; // 30 min cool-down once tripped

interface SyncStateRow {
  consecutive_failures: number;
  opened_until: string | null;
  last_success_at: string | null;
}

export class CircuitBreaker {
  constructor(private readonly supabase: SupabaseClient) {}

  /** Returns true when the breaker is open and the sync run should be skipped. */
  async isOpen(): Promise<boolean> {
    const { data, error } = await this.supabase
      .from("sync_state")
      .select("opened_until")
      .eq("id", true)
      .single<Pick<SyncStateRow, "opened_until">>();

    if (error || !data?.opened_until) return false;
    return new Date(data.opened_until).getTime() > Date.now();
  }

  async recordSuccess(): Promise<void> {
    await this.supabase
      .from("sync_state")
      .update({
        consecutive_failures: 0,
        opened_until: null,
        last_success_at: new Date().toISOString(),
      })
      .eq("id", true);
  }

  async recordFailure(): Promise<void> {
    const { data } = await this.supabase
      .from("sync_state")
      .select("consecutive_failures")
      .eq("id", true)
      .single<Pick<SyncStateRow, "consecutive_failures">>();

    const failures = (data?.consecutive_failures ?? 0) + 1;
    const shouldOpen = failures >= FAILURE_THRESHOLD;

    await this.supabase
      .from("sync_state")
      .update({
        consecutive_failures: failures,
        opened_until: shouldOpen
          ? new Date(Date.now() + OPEN_DURATION_MS).toISOString()
          : null,
      })
      .eq("id", true);
  }
}
