-- PokeApp Supabase V2 greenfield schema.
-- 007_competitions: generic cup tables, trials/cases and penalties.

begin;

create table public.cups (
  id uuid primary key default gen_random_uuid(),
  season_id uuid references public.seasons(id) on delete restrict,
  name text not null,
  competition_type text not null default 'cup',
  format text not null,
  status text not null default 'draft',
  started_at timestamptz,
  finished_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint cups_name_chk
    check (length(btrim(name)) > 0),
  constraint cups_competition_type_chk
    check (competition_type in ('cup', 'tournament', 'doubles_cup')),
  constraint cups_format_chk
    check (format in ('swiss', 'elimination', 'doubles', 'manual')),
  constraint cups_status_chk
    check (status in ('draft', 'active', 'finished', 'archived', 'discarded'))
);

create trigger cups_set_updated_at
before update on public.cups
for each row execute function public.set_updated_at();

comment on table public.cups is
  'Generic cup/tournament container. Swiss, elimination and doubles share one model through format.';

create table public.cup_participants (
  id uuid primary key default gen_random_uuid(),
  cup_id uuid not null references public.cups(id) on delete restrict,
  trainer_id uuid references public.trainers(id) on delete restrict,
  display_name text not null,
  seed_order integer,
  status text not null default 'active',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint cup_participants_display_name_chk
    check (length(btrim(display_name)) > 0),
  constraint cup_participants_seed_order_chk
    check (seed_order is null or seed_order > 0),
  constraint cup_participants_status_chk
    check (status in ('active', 'eliminated', 'dropped', 'disqualified'))
);

comment on table public.cup_participants is
  'Cup sides. For doubles/team cups, trainer_id can be null and metadata can carry member ids until product needs a richer team model.';

create table public.cup_matches (
  id uuid primary key default gen_random_uuid(),
  cup_id uuid not null references public.cups(id) on delete restrict,
  round_number integer not null,
  bracket_position integer,
  participant_a_id uuid references public.cup_participants(id) on delete restrict,
  participant_b_id uuid references public.cup_participants(id) on delete restrict,
  winner_participant_id uuid references public.cup_participants(id) on delete restrict,
  status text not null default 'scheduled',
  score text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint cup_matches_round_number_chk
    check (round_number > 0),
  constraint cup_matches_bracket_position_chk
    check (bracket_position is null or bracket_position > 0),
  constraint cup_matches_status_chk
    check (status in ('scheduled', 'completed', 'forfeit', 'bye', 'void')),
  constraint cup_matches_winner_is_side_chk
    check (
      winner_participant_id is null
      or winner_participant_id = participant_a_id
      or winner_participant_id = participant_b_id
    )
);

create trigger cup_matches_set_updated_at
before update on public.cup_matches
for each row execute function public.set_updated_at();

create table public.cup_standings (
  id uuid primary key default gen_random_uuid(),
  cup_id uuid not null references public.cups(id) on delete restrict,
  participant_id uuid not null references public.cup_participants(id) on delete restrict,
  position integer,
  points numeric(6, 2) not null default 0,
  wins integer not null default 0,
  losses integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint cup_standings_position_chk
    check (position is null or position > 0),
  constraint cup_standings_record_chk
    check (wins >= 0 and losses >= 0),
  constraint uq_cup_standings_participant
    unique (cup_id, participant_id)
);

create trigger cup_standings_set_updated_at
before update on public.cup_standings
for each row execute function public.set_updated_at();

create table public.trial_cases (
  id uuid primary key default gen_random_uuid(),
  season_id uuid references public.seasons(id) on delete restrict,
  matchday_id uuid,
  accused_trainer_id uuid references public.trainers(id) on delete restrict,
  created_by_trainer_id uuid references public.trainers(id) on delete set null,
  title text not null,
  description text not null default '',
  status text not null default 'open',
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  updated_at timestamptz not null default now(),
  constraint trial_cases_title_chk
    check (length(btrim(title)) > 0),
  constraint trial_cases_status_chk
    check (status in ('open', 'resolved', 'dismissed', 'cancelled')),
  constraint trial_cases_matchday_requires_season_chk
    check (matchday_id is null or season_id is not null),
  constraint fk_trial_cases_matchday_same_season
    foreign key (matchday_id, season_id)
    references public.matchdays(id, season_id)
    on delete restrict
);

create trigger trial_cases_set_updated_at
before update on public.trial_cases
for each row execute function public.set_updated_at();

create table public.trial_votes (
  id uuid primary key default gen_random_uuid(),
  trial_case_id uuid not null references public.trial_cases(id) on delete restrict,
  voter_trainer_id uuid not null references public.trainers(id) on delete restrict,
  vote text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint trial_votes_vote_chk
    check (vote in ('guilty', 'not_guilty', 'abstain', 'other')),
  constraint uq_trial_votes_case_voter
    unique (trial_case_id, voter_trainer_id)
);

create table public.penalties (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  trainer_id uuid not null references public.trainers(id) on delete restrict,
  matchday_id uuid,
  trial_case_id uuid references public.trial_cases(id) on delete restrict,
  penalty_type text not null,
  amount integer not null default 0,
  payload jsonb not null default '{}'::jsonb,
  created_by_trainer_id uuid references public.trainers(id) on delete set null,
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  constraint penalties_type_chk
    check (length(btrim(penalty_type)) > 0),
  constraint fk_penalties_matchday_same_season
    foreign key (matchday_id, season_id)
    references public.matchdays(id, season_id)
    on delete restrict
);

comment on table public.penalties is
  'Official penalties from trials/admin. Effects can be matchday-scoped and are reflected in snapshots/ledger by application logic.';

commit;
