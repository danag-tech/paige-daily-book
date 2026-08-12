-- Dedicated low-privilege Supabase keepalive endpoint.
-- This table contains no user data and exposes only id=1 to the anon role.

create table if not exists public.keepalive (
    id smallint primary key,
    status text not null,
    created_at timestamptz not null default now()
);

insert into public.keepalive (id, status)
values (1, 'ok')
on conflict (id) do nothing;

alter table public.keepalive enable row level security;

revoke all on table public.keepalive from public, anon, authenticated;
grant select on table public.keepalive to anon;

drop policy if exists "keepalive_read_anon" on public.keepalive;

create policy "keepalive_read_anon"
on public.keepalive
for select
to anon
using (id = 1);
