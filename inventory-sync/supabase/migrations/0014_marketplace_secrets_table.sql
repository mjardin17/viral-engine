-- Encryption key storage for tenant_marketplace_connections.
--
-- Supabase's hosted Postgres does not permit custom GUC parameters —
-- confirmed directly: both `ALTER DATABASE ... SET app.x` and
-- `ALTER FUNCTION ... SET app.x` return `42501: permission denied to set
-- parameter`, even via the CLI's own database-owner connection. That rules
-- out the usual current_setting('app.x') pattern entirely on this platform.
--
-- Replacement: a single-row table, RLS enabled with NO policies granted to
-- anon or authenticated (so it's unreachable via PostgREST/the client SDK
-- no matter what), read only from inside the SECURITY DEFINER functions,
-- which run as the functions' owner and are therefore not subject to RLS
-- on tables owned by that same role.
--
-- The actual key value is deliberately NOT in this file — it's inserted via
-- a separate `supabase db query --linked` command outside of migration
-- history, so the real secret never lands in a file that gets committed to
-- git. This file only creates the empty table.
create table if not exists public._marketplace_secrets (
  id         int primary key default 1 check (id = 1), -- enforce single row
  key_value  text not null
);

alter table public._marketplace_secrets enable row level security;
revoke all on public._marketplace_secrets from anon, authenticated;
-- No policies created at all — RLS with zero policies denies every row to
-- every role except the table owner, which is exactly the point.

-- Replace the two functions that referenced current_setting('app.x') with
-- versions that read the key from this table instead.
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
  v_key text;
  v_encrypted bytea;
begin
  select key_value into v_key from public._marketplace_secrets where id = 1;
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

grant execute on function public.store_marketplace_connection(text, text, text, text) to authenticated;
revoke all on function public.get_decrypted_marketplace_token(uuid, text, text) from public, anon, authenticated;
grant execute on function public.get_decrypted_marketplace_token(uuid, text, text) to service_role;
