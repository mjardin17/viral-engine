// Exchanges the long-lived eBay refresh token (obtained once via the
// 3-legged OAuth consent flow — see inventory-sync/DEPLOY.md) for a
// short-lived access token. Re-run on every invocation since the sync
// only fires every 15 minutes; no need to cache across runs.

import { HttpStatusError } from "./retry.ts";

export interface EbayEnv {
  clientId: string;
  clientSecret: string;
  refreshToken: string;
  /** "production" | "sandbox" */
  environment: string;
}

const SCOPE = "https://api.ebay.com/oauth/api_scope/sell.inventory";

function tokenUrl(environment: string): string {
  return environment === "sandbox"
    ? "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    : "https://api.ebay.com/identity/v1/oauth2/token";
}

export async function getEbayAccessToken(env: EbayEnv): Promise<string> {
  const credentials = btoa(`${env.clientId}:${env.clientSecret}`);
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    refresh_token: env.refreshToken,
    scope: SCOPE,
  });

  const response = await fetch(tokenUrl(env.environment), {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Basic ${credentials}`,
    },
    body,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new HttpStatusError(
      response.status,
      `eBay OAuth token exchange failed (${response.status}): ${detail}`,
    );
  }

  const payload = await response.json() as { access_token: string };
  return payload.access_token;
}
