# Sync reports

`sync_logs` (Postgres, `public.sync_logs`) is the source of truth for every
ebay-sync run — an Edge Function has no persistent filesystem to write a
report file to at runtime, so structured rows in Postgres replace what would
otherwise be a flat log file.

To pull a markdown-style snapshot on demand, run in the Supabase SQL Editor:

```sql
select
  started_at,
  status,
  items_seen,
  items_upserted,
  jsonb_array_length(conflicts) as conflict_count,
  jsonb_array_length(errors) as error_count
from public.sync_logs
order by started_at desc
limit 20;
```

To inspect the actual conflicts/errors from the most recent run:

```sql
select conflicts, errors
from public.sync_logs
order by started_at desc
limit 1;
```

Failures older than 30 days are cheap to prune (Postgres free tier storage
is limited):

```sql
delete from public.sync_logs where started_at < now() - interval '30 days';
```
