-- Reverts 0010 and 0011. Both were unnecessary and one was actively wrong.
--
-- Root cause of the confusion: I read the earlier "permission denied for
-- table products" error as a bug and granted anon direct SELECT on
-- public.products. It wasn't a bug — migration 0008 deliberately revoked
-- that grant on purpose (see functions/api/products.ts's own comment:
-- "the raw table carries cost/sync/tenant bookkeeping that must not be
-- publicly readable"). The real public interface is the storefront_products
-- VIEW, which already had the correct anon SELECT grant the whole time —
-- verified directly, not assumed, before writing this revert.
--
-- 0011's my_tenant_ids() EXECUTE grant to anon is reverted for the same
-- reason: it existed only to make direct anon reads of public.products
-- work, which anon was never supposed to do in the first place.
revoke select on public.products from anon;
revoke execute on function public.my_tenant_ids() from anon;
