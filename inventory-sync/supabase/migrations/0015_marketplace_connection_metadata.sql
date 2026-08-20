-- Etsy needs a per-tenant shop_id for every listing call
-- (POST /v3/application/shops/{shop_id}/listings) — eBay had no equivalent
-- ("merchant_location_key" is a shared app-level value, not per-tenant), so
-- tenant_marketplace_connections (migration 0013) never needed a slot for
-- platform-specific extras. Generic `metadata jsonb` instead of an
-- `etsy_shop_id` column so the next platform with its own required extra
-- field (if any) doesn't need its own migration too.

alter table public.tenant_marketplace_connections
  add column if not exists metadata jsonb;

-- store_marketplace_connection gains an optional p_metadata param.
-- Signature change (new trailing default arg) is backward compatible —
-- existing callers (eBay's callback route) that don't pass it keep working.
create or replace function public.store_marketplace_connection(
  p_marketplace text,
  p_environment text,
  p_refresh_token text,
  p_account_identifier text default null,
  p_metadata jsonb default null
) returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  v_tenant_id uuid;
  v_key text;
begin
  select key_value into v_key from public._marketplace_secrets where id = 1;
  if v_key is null or length(v_key) = 0 then
    raise exception 'MARKETPLACE_TOKEN_KEY_NOT_SET: run the key-insert step first';
  end if;

  select tenant_id into v_tenant_id
  from public.tenant_members
  where user_id = auth.uid()
  limit 1;

  if v_tenant_id is null then
    raise exception 'NO_TENANT: authenticated user has no tenant membership';
  end if;

  insert into public.tenant_marketplace_connections
    (tenant_id, marketplace, environment, encrypted_refresh_token, account_identifier, metadata)
  values
    (v_tenant_id, p_marketplace, p_environment,
     pgp_sym_encrypt(p_refresh_token, v_key), p_account_identifier, p_metadata)
  on conflict (tenant_id, marketplace, environment) do update set
    encrypted_refresh_token = excluded.encrypted_refresh_token,
    account_identifier = excluded.account_identifier,
    metadata = excluded.metadata,
    updated_at = now();

  return true;
end;
$$;

-- get_marketplace_connection_status now also returns metadata (non-secret —
-- safe to hand back to the tenant's own browser, unlike the token itself).
-- Table shape changed, so the function must be dropped first — Postgres
-- refuses CREATE OR REPLACE across a returns-table column change.
drop function if exists public.get_marketplace_connection_status(text);

create function public.get_marketplace_connection_status(
  p_marketplace text
) returns table (connected boolean, account_identifier text, connected_at timestamptz, metadata jsonb)
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
    return query select false, null::text, null::timestamptz, null::jsonb;
    return;
  end if;

  return query
    select true, c.account_identifier, c.connected_at, c.metadata
    from public.tenant_marketplace_connections c
    where c.tenant_id = v_tenant_id and c.marketplace = p_marketplace
    limit 1;

  if not found then
    return query select false, null::text, null::timestamptz, null::jsonb;
  end if;
end;
$$;

-- Service-role-only lookup of a tenant's metadata (e.g. Etsy shop_id) by
-- tenant_id directly — mirrors get_decrypted_marketplace_token's security
-- model (called from the API route with the service_role key, not from the
-- customer's own session, since p_tenant_id is passed explicitly rather
-- than resolved from auth.uid()). Metadata isn't secret, but the lookup
-- path is still service_role-only for consistency with how the API route
-- already authenticates for get_decrypted_marketplace_token.
create or replace function public.get_marketplace_connection_metadata(
  p_tenant_id uuid,
  p_marketplace text,
  p_environment text default 'production'
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_metadata jsonb;
begin
  select metadata into v_metadata
  from public.tenant_marketplace_connections
  where tenant_id = p_tenant_id and marketplace = p_marketplace and environment = p_environment;

  return v_metadata;
end;
$$;

revoke all on function public.get_marketplace_connection_metadata(uuid, text, text) from public, anon, authenticated;
grant execute on function public.get_marketplace_connection_metadata(uuid, text, text) to service_role;

grant execute on function public.store_marketplace_connection(text, text, text, text, jsonb) to authenticated;
grant execute on function public.get_marketplace_connection_status(text) to authenticated;
