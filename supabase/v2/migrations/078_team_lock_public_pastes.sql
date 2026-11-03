-- 078_team_lock_public_pastes: the public Pokepast.es link of a confirmed
-- Team Lock announcement (067 outbox).
--
-- The API creates the paste from the lock's public_team_snapshot only (never
-- the private snapshot, saves or evidence) right before announcing it, and
-- records the link here first, so a retried or edited Discord message reuses
-- it instead of publishing the same team twice. A replaced lock raises the
-- announcement revision (067 trigger): its link no longer matches and a new
-- paste is made for the new team; the old link is never shown for it.
-- Failed attempts are counted per revision and bounded by the API; a failure
-- only delays the announcement briefly and then it is posted without a link.
-- Team Locks themselves are not touched by this migration.
begin;

alter table public.discord_announcements
  add column public_paste_url text
    check (public_paste_url ~ '^https://pokepast\.es/[0-9a-f]{16}$'),
  add column public_paste_revision integer
    check (public_paste_revision > 0),
  add column public_paste_attempt_revision integer not null default 0
    check (public_paste_attempt_revision >= 0),
  add column public_paste_attempts integer not null default 0
    check (public_paste_attempts between 0 and 10),
  add column public_paste_error text
    check (public_paste_error ~ '^[a-z0-9_]{1,64}$'),
  add constraint discord_announcements_public_paste_pair
    check ((public_paste_url is null) = (public_paste_revision is null)),
  add constraint discord_announcements_public_paste_current
    check (public_paste_revision is null or public_paste_revision <= revision),
  add constraint discord_announcements_public_paste_attempt_current
    check (public_paste_attempt_revision <= revision),
  add constraint discord_announcements_public_paste_team_lock_only
    check (kind = 'team_locked' or (public_paste_url is null
      and public_paste_attempt_revision = 0 and public_paste_attempts = 0
      and public_paste_error is null));

comment on column public.discord_announcements.public_paste_url is
  'Public Pokepast.es link of the team_locked announcement, created from public_team_snapshot only.';
comment on column public.discord_announcements.public_paste_revision is
  'Announcement revision whose public team the link shows; a newer revision needs a new paste.';
comment on column public.discord_announcements.public_paste_attempts is
  'Failed paste attempts for public_paste_attempt_revision (bounded by the API).';

notify pgrst, 'reload schema';
commit;
