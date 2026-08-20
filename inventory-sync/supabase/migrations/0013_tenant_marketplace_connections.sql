-- Per-tenant marketplace OAuth connections. This is the missing piece for
-- "customer clicks Connect eBay" instead of "customer pastes API keys" —
-- each tenant's refresh token is stored encrypted, scoped to their own
-- tenant_id, never readable in plaintext outside a SECURITY DEFINER
-- function running server-side.
--
-- Follows the exact pattern already established by create_tenant_for_user
-- (migration 0005-0009, undocumented until this session found it): a
-- SECURITY DEFINER RPC that resolves auth.uid() -> tenant internally, so
-- the client only ever needs its own Supabase Auth session token — never
-- a service_role key, never a raw encryption key.

create table if not exists public.tenant_marketplace_connections (
  id                    uuid primary key default gen_random_uuid(),
  tenant_id             uuid not null references public.tenants(id) on delete cascade,
  marketplace           text not null check (marketplace in (
                          'ebay','etsy','shopify','woocommerce')),
  environment           text not null default 'production'
                          check (environment in ('production','sandbox')),
  encrypted_refresh_token bytea not null,
  account_identifier    text,
  connected_at          timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (tenant_id, marketplace, environment)
);

drop trigger if exists tenant_marketplace_connections_set_updated_at
  on public.tenant_marketplace_connections;
create trigger tenant_marketplace_connections_set_updated_at
  before update on public.tenant_marketplace_connections
  for each row execute function public.set_updated_at();

alter table public.tenant_marketplace_connections enable row level security;

-- No direct client access at all, in either direction — every read/write
-- goes through the SECURITY DEFINER RPCs below. This is stricter than
-- "tenant can read their own row" on purpose: even a decrypted-looking
-- column name in a REST response is a mistake waiting to happen. The RPCs
-- return only a boolean/status, never the token itself, back to the client.
revoke all on public.tenant_marketplace_connections from anon, authenticated;

-- Store (insert or replace) a tenant's refresh token for a marketplace.
-- Runs as the calling user; resolves their tenant via tenant_members so a
-- caller can never write into a tenant they don't belong to.
create or replace function public.store_marketplace_connection(
  p_marketplace text,
  p_environment text,
  p_refresh_token text,
  p_account_identifier text default null
) returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  v_tenant_id uuid;
  v_key text := current_setting('app.marketplace_token_key', true);
begin
  if v_key is null or length(v_key) = 0 then
    raise exception 'MARKETPLACE_TOKEN_KEY_NOT_SET: encryption key is not configured on this database';
  end if;

  select tenant_id into v_tenant_id
  from public.tenant_members
  where user_id = auth.uid()
  limit 1;

  if v_tenant_id is null then
    raise exception 'NO_TENANT: authenticated user has no tenant membership';
  end if;

  insert into public.tenant_marketplace_connections
    (tenant_id, marketplace, environment, encrypted_refresh_token, account_identifier)
  values
    (v_tenant_id, p_marketplace, p_environment,
     pgp_sym_encrypt(p_refresh_token, v_key), p_account_identifier)
  on conflict (tenant_id, marketplace, environment) do update set
    encrypted_refresh_token = excluded.encrypted_refresh_token,
    account_identifier = excluded.account_identifier,
    updated_at = now();

  return true;
end;
$$;

-- Returns connection STATUS only (never the decrypted token) for the
-- calling user's tenant. This is what the /channels-style UI calls.
create or replace function public.get_marketplace_connection_status(
  p_marketplace text
) returns table (connected boolean, account_identifier text, connected_at timestamptz)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_tenant_id uuid;
begin
  select tenant_id into v_tenant_id
  from public.tenant_members
  where user_id = auth.uid()
  limit 1;

  if v_tenant_id is null then
    return query select false, null::text, null::timestamptz;
    return;
  end if;

  return query
    select true, c.account_identifier, c.connected_at
    from public.tenant_marketplace_connections c
    where c.tenant_id = v_tenant_id and c.marketplace = p_marketplace
    limit 1;

  if not found then
    return query select false, null::text, null::timestamptz;
  end if;
end;
$$;

-- Decrypts and returns a tenant's refresh token — ONLY callable with the
-- app's own service_role key (never exposed to a customer's browser).
-- This is what the Next.js API route calls server-side when it needs to
-- actually refresh an access token or create a listing on the tenant's
-- behalf, using the app's shared EBAY_CLIENT_ID/SECRET as before.
create or replace function public.get_decrypted_marketplace_token(
  p_tenant_id uuid,
  p_marketplace text,
  p_environment text default 'production'
) returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  v_key text := current_setting('app.marketplace_token_key', true);
  v_encrypted bytea;
begin
  if v_key is null or length(v_key) = 0 then
    raise exception 'MARKETPLACE_TOKEN_KEY_NOT_SET';
  end if;

  select encrypted_refresh_token into v_encrypted
  from public.tenant_marketplace_connections
  where tenant_id = p_tenant_id and marketplace = p_marketplace and environment = p_environment;

  if v_encrypted is null then
    return null;
  end if;

  return pgp_sym_decrypt(v_encrypted, v_key);
end;
$$;

-- Grants: authenticated users can call the two customer-facing RPCs
-- (store/status), both scoped internally to their own tenant. Only
-- service_role can call the decrypt function — enforced by revoking it
-- from everyone else explicitly, since SECURITY DEFINER functions are
-- PUBLIC-callable by default otherwise.
revoke all on function public.get_decrypted_marketplace_token(uuid, text, text) from public, anon, authenticated;
grant execute on function public.get_decrypted_marketplace_token(uuid, text, text) to service_role;

grant execute on function public.store_marketplace_connection(text, text, text, text) to authenticated;
grant execute on function public.get_marketplace_connection_status(text) to authenticated;
