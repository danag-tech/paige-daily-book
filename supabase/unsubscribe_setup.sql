-- Paige Daily Book V1.3 subscription lifecycle setup.
-- Run this in the Supabase SQL editor as a database owner.

create extension if not exists pgcrypto;

alter table public.subscribers
  add column if not exists unsubscribe_token uuid;

update public.subscribers
set unsubscribe_token = gen_random_uuid()
where unsubscribe_token is null;

alter table public.subscribers
  alter column unsubscribe_token set default gen_random_uuid(),
  alter column unsubscribe_token set not null;

create unique index if not exists subscribers_unsubscribe_token_unique
  on public.subscribers (unsubscribe_token);

-- Keep one normalized email record so re-subscription never creates duplicates.
create unique index if not exists subscribers_email_normalized_unique
  on public.subscribers (lower(trim(email)));

create or replace function public.subscribe_by_email(email text)
returns text
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  normalized_email text := lower(trim(email));
  existing_active boolean;
begin
  if normalized_email is null or normalized_email = '' then
    raise exception 'email is required';
  end if;

  select active
    into existing_active
    from public.subscribers
   where lower(trim(subscribers.email)) = normalized_email
   limit 1;

  if found then
    if existing_active then
      return 'already_subscribed';
    end if;

    update public.subscribers
       set active = true
     where lower(trim(subscribers.email)) = normalized_email;
    return 'resubscribed';
  end if;

  insert into public.subscribers (email, active)
  values (normalized_email, true);
  return 'subscribed';
end;
$$;

drop function if exists public.unsubscribe_by_token(uuid);

create or replace function public.unsubscribe_by_token(token uuid)
returns text
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
  if not exists (
    select 1
      from public.subscribers
     where unsubscribe_token = token
  ) then
    return 'invalid_token';
  end if;

  if exists (
    select 1
      from public.subscribers
     where unsubscribe_token = token
       and active is false
  ) then
    return 'already_unsubscribed';
  end if;

  update public.subscribers
     set active = false
   where unsubscribe_token = token;
  return 'unsubscribed';
end;
$$;

-- The browser may execute only the two controlled lifecycle functions.
revoke all on table public.subscribers from public, anon, authenticated;
revoke all on function public.subscribe_by_email(text) from public;
revoke all on function public.unsubscribe_by_token(uuid) from public;
grant execute on function public.subscribe_by_email(text) to anon, authenticated;
grant execute on function public.unsubscribe_by_token(uuid) to anon, authenticated;