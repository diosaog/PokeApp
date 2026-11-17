"""086/087 on a restored production copy: exactly which rows they change.

086 deliberately rewrites closed jornadas whose order changes under the direct
match rule. The rehearsal therefore proves, row by row, that ONLY these change:

* matchday_snapshots: the re-ranked jornadas (one revision more);
* matchday_snapshot_revisions: one new «h2h_tiebreak_rule» revision each;
* purchases: an unused moved prize cancelled, its new pending reward issued;
* matchdays: the re-ranked jornadas' revision counter;
* activity_events: one MATCHDAY_ADMIN_CORRECT (source 086) each;
* discord_announcements: one queued «matchday_corrected» each;
* purchases (087): every unused «Blindaje por Robo» voucher cancelled.

and reports, by display name, the previous and the new order and every prize
that moves, for the owner to read before production.
"""

from __future__ import annotations

TABLES = (
    "public.matchday_snapshots",
    "public.matchday_snapshot_revisions",
    "public.purchases",
    "public.matchdays",
    "public.activity_events",
    "public.discord_announcements",
)


def row_hashes(pg) -> dict[str, dict[str, str]]:
    result = {}
    for table in TABLES:
        lines = pg.lines(f"select t.id::text||' '||md5(to_jsonb(t)::text) from {table} t", "supabase_admin")
        result[table] = dict(line.split(" ", 1) for line in lines)
    return result


def dependent_views(pg) -> set[str]:
    """public views that read (directly or through other views) a changed table."""
    names = ",".join(f"'{t}'::regclass" for t in TABLES)
    return set(pg.lines(f"""with recursive dep(oid) as (
        select unnest(array[{names}])::oid
        union
        select r.ev_class from pg_depend d join pg_rewrite r on r.oid=d.objid join dep on dep.oid=d.refobjid
        where r.ev_class<>d.refobjid)
      select 'view '||n.nspname||'.'||c.relname from dep join pg_class c on c.oid=dep.oid
        join pg_namespace n on n.oid=c.relnamespace where c.relkind='v' and n.nspname='public' order by 1""",
        "supabase_admin"))


def _voucher(alias: str = "") -> str:
    """087: an unused «Blindaje por Robo» voucher cancelled by the migration."""
    a = f"{alias}." if alias else ""
    return (f"{a}status='cancelled' and {a}metadata->>'cancelled_by_migration'='087' and {a}shop_item_id in"
            " (select id from public.shop_items where code='robbery_shield_voucher')")


def _ids(values) -> str:
    return ",".join(f"'{v}'" for v in values) or "null"


def verify(pg, before: dict[str, dict[str, str]]) -> dict:
    """Return the re-ranking report; 'problems' lists any unexpected change."""
    after = row_hashes(pg)
    changed, added, problems = {}, {}, []
    for table in TABLES:
        old, new = before[table], after[table]
        if set(old) - set(new):
            problems.append(f"{table}: rows removed")
        changed[table] = sorted(k for k in old if k in new and old[k] != new[k])
        added[table] = sorted(set(new) - set(old))
    days = pg.lines(
        f"select distinct matchday_id::text from public.matchday_snapshot_revisions where id in ({_ids(added['public.matchday_snapshot_revisions'])})"
        " and snapshot->'correction'->>'kind'='h2h_tiebreak_rule' order by 1", "supabase_admin")
    day_list = _ids(days)

    def outside(table, sql_condition, rows):
        if not rows:
            return
        bad = pg.lines(f"select id::text from {table} where id in ({_ids(rows)}) and not ({sql_condition})", "supabase_admin")
        if bad:
            problems.append(f"{table}: unexpected rows {bad}")

    if changed["public.matchday_snapshot_revisions"]:
        problems.append("matchday_snapshot_revisions: existing revision modified")
    outside("public.matchday_snapshot_revisions",
            "snapshot->'correction'->>'kind'='h2h_tiebreak_rule'", added["public.matchday_snapshot_revisions"])
    if added["public.matchday_snapshots"] or added["public.matchdays"]:
        problems.append("new snapshots or jornadas created")
    outside("public.matchday_snapshots", f"matchday_id in ({day_list})", changed["public.matchday_snapshots"])
    outside("public.matchdays", f"id in ({day_list})", changed["public.matchdays"])
    outside("public.purchases", f"(origin_matchday_id in ({day_list}) and status='cancelled'"
            f" and metadata ? 'cancelled_by_revision') or ({_voucher()})", changed["public.purchases"])
    retired = pg.lines(f"""select t.display_name||' '||count(*) from public.purchases p
        join public.trainers t on t.id=p.trainer_id where p.id in ({_ids(changed['public.purchases'])})
        and {_voucher('p')} group by t.display_name order by 1""", "supabase_admin")
    outside("public.purchases", f"origin_matchday_id in ({day_list}) and status='pending'"
            " and acquisition_type='reward' and unit_price=0", added["public.purchases"])
    for table in ("public.activity_events", "public.discord_announcements"):
        if changed[table]:
            problems.append(f"{table}: existing rows modified")
    outside("public.activity_events", "type='MATCHDAY_ADMIN_CORRECT' and payload->>'source'='086_h2h_tiebreak'",
            added["public.activity_events"])
    outside("public.discord_announcements", "kind='matchday_corrected'", added["public.discord_announcements"])
    counts = {t: len(added[t]) for t in TABLES}
    if days and not (counts["public.matchday_snapshot_revisions"] == counts["public.activity_events"]
                     == counts["public.discord_announcements"] == len(days)):
        problems.append(f"one revision, event and announcement per re-ranked jornada expected: {counts}")
    if not days and any(changed[t] or added[t] for t in TABLES if t != "public.purchases"):
        problems.append("rows changed although no jornada was re-ranked")
    if not days and (added["public.purchases"] or (changed["public.purchases"] and not retired)):
        problems.append("purchases changed although no jornada was re-ranked nor voucher retired")

    jornadas = []
    for day in days:
        lines = pg.lines(f"""select d.number||'|'||s.revision||'|'||
            (select string_agg(t.display_name||' '||(x->>'position')||coalesce(' ['||(x#>>'{{metadata,tiebreak}}')||']',''),', '
               order by (x#>>'{{metadata,allocation_position}}')::integer)
             from jsonb_array_elements(s.snapshot->'standings') x join public.season_players p on p.id=(x->>'trainer_id')::uuid
             join public.trainers t on t.id=p.trainer_id)||'|'||
            (select string_agg(t.display_name||' '||(x->>'position'),', ' order by (x#>>'{{metadata,allocation_position}}')::integer)
             from public.matchday_snapshot_revisions r, jsonb_array_elements(r.snapshot->'standings') x
             join public.season_players p on p.id=(x->>'trainer_id')::uuid join public.trainers t on t.id=p.trainer_id
             where r.matchday_id=d.id and r.revision=s.revision-1)
          from public.matchdays d join public.matchday_snapshots s on s.matchday_id=d.id where d.id='{day}'""",
            "supabase_admin")
        number, revision, new_order, old_order = lines[0].split("|")
        moves = pg.lines(f"""select i.code||' '||p.status||' '||t.display_name from public.purchases p
            join public.shop_items i on i.id=p.shop_item_id join public.trainers t on t.id=p.trainer_id
            where p.id in ({_ids(changed['public.purchases'] + added['public.purchases'])}) and p.origin_matchday_id='{day}'
            order by 1""", "supabase_admin")
        jornadas.append(dict(jornada=int(number), revision=int(revision), before=old_order, after=new_order,
                             prize_moves=moves))
    return dict(rule="wins_h2h_deaths_v3", reranked=jornadas, retired_vouchers=retired, counts=counts,
                problems=problems)
