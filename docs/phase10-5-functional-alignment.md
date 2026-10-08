# Phase 10.5 — Functional product alignment and repair

Approved owner instruction: 2026-09-29, implementation before migration.
[Live execution record](work-in-progress/phase10-5-live-handoff.md),
[continuity](AI/PokeApp_Multi_AI_Continuity_Protocol.md),
[previous delivery](phase10-completion-report.md).

Phase 10 remains DONE for its delivered scope. Phase 10.5 corrects product
semantics established by the subsequent functional review. Phase 11 is NOT STARTED
and requires owner + ChatGPT review after this phase. This is not a rewrite.

Current 2026-10-08: **PHASE 10.5 DONE; A–M + final alignment delivered**.
[Final report](phase10-5-completion-report.md). **Phase 11 READY FOR REVIEW /
NOT STARTED**. Older dated stopping points and gap statements below are historical.

## Approved behavior and order of execution

Each package ends with focused green checks, documentation and a pushed coherent
commit before the next starts. Deploy at stable checkpoints, not every commit.

| Package | Required behavior |
|---|---|
| A | Verify actual entry and publish the alignment matrix and resumable memory. |
| B | Server-authoritative GENERAL: trainer, exact accumulated official points, current coins, observed dead count or explicit unknown. Sort points descending; stable secondary display order never resolves a sporting tie. GENERAL/current/completed J tabs; preserve daily Top 3 and A/B. |
| C | Any enabled, active, eligible season participant records/edits any editable current match, including matches between other participants. Verified JWT identity, season scope, CAS and stable idempotency; closed-day admin correction stays separate. Ordinary entry belongs in League/Battles. |
| D | Daily wins descending then fewer adjusted deaths. No H2H-first two-way rule; no alphabetical sporting resolution. Auditable exceptional resolution where unresolved ties affect rewards/movement/cuts. |
| E | First game segment before initial A/B. Observed save progress/death readiness, suggested split by fewer deaths, external resolution only for a relevant cut tie. Exact capacities and immutable recorded assignment; missing observations block readiness. No manual medal attestation. |
| F | Finish/Hall uses final accumulated official points, not final day's position. Exactly two tied leaders require audited external BO3; 3+ use fewer frozen authoritative adjusted deaths, then audited external resolution restricted to the remaining minimum-death candidates. Final alignment implements this extension. Finalist remains undefined. Existing frozen history never silently rewritten. |
| G | Participant-owned nonnegative audited/idempotent wipe counter, current applicability only. Box 8 (legacy index 7) deaths cost 0.2 each without a cap; each wipe revival costs 0.4. Five visible dead plus one wipe revival costs 1.4. |
| H | Strong missing-Team-Lock warning with ability to continue. Batallas / Team Preview: two distinct independent public selectors in Espectador; one selector including self in Batalla, own private detail permitted, rivals public only. |
| I | Exact wallet strings; public pending/active promotions; owned robbery-shield voucher redemption; post-League spending; configurable observed-save badge/Champion rewards; purchased-revive death overlap. |
| J | Human Spanish readiness/error wording in Admin; setup, supervision, exceptions, history and risk actions. Preserve server revisions/CAS. |
| K | Explicit public competitive Team Lock scouting: species, nickname, level, types, item and moves only. Reuse H; self/admin remain public here. No save/PC/box/identity fallback. |
| L | Reuse E regional badge evidence and I reader/3 nullable Champion proof. Current owned/latest accepted save observations distinguish unknown, observed zero and Champion true/false/unknown. Eight badges are not game completion. Participant presentation preserves regional badge identity; no manual attestation, duplicate reward engine or full cloud ingestion. |
| M | DONE: measured current read flows; cold Shop no longer fetches overview for redemption names. Public names load on demand. [Report](phase10-5m-completion-report.md), [ranked Phase 14 / final alignment candidates](phase10-5m-performance-candidates.md). No broad performance refactor. |

Three distinct truths remain: real save state, competitive state and frozen
official history. A new save cannot rewrite closed results. A registered virtual
revive/theft is not proof of a physical save mutation. Current judicial manual
Discord verdicts and modern 8L Cup rules are intentional V2 improvements.

## Package D contract detail (approved continuation, 2026-10-01)

The same wins/adjusted-deaths rule applies to every group size. Adjusted deaths
reuse the existing 030 integer sources: Box 8 observations plus the greater of
applied revivals and used revive purchases, plus twice the wipe-revival counter.
I subtracts proven overlap with a purchased revive still visible in Box 8, so the
same death counts once. An intervening alive observation proves a later death is
new; ambiguous/unlinked legacy overlap remains UNKNOWN. Frozen correction inputs
are preserved. The visible Box 8 count delivered by B is a separate fact.

A residual daily tie requires external resolution only when group members would
receive different position points, position coins, unique Top 3 places, movement
outcomes or the last-B theft reward. Otherwise they share a sporting position;
technical member order must not affect those consequences. An admin may record
the externally agreed complete group order and reason, bound to current review
inputs. This is an audited exception using existing close/correction authority,
not an automated sporting tie-break. Initial A/B and final championship rules
remain E/F and the unresolved owner decisions below.

Existing schema-2 snapshots remain unchanged. Future closes identify
`wins_adjusted_deaths_v1` in frozen inputs; corrections preserve that recorded rule.
Pre-D snapshots retain `legacy_pre_10_5d` semantics on controlled correction.
External decisions are append-only snapshot history with the existing actor,
timestamp, revision and receipt. They are official history, not private messages;
the typed frontend projection includes shared position/status only. Internal
allocation slots prove completeness without claiming unique sporting places.

Public verification must preserve manual owner seasons: positive tie mutations,
rollback and concurrency are local evidence; hosted auth/reads and guaranteed
absent-resource denials are separate evidence. Additive 035 is necessary for the
rule/audit/lifecycle distinction; never replay 001–034.

## Package E contract detail (approved continuation, 2026-10-01)

Jornada 1 covers the first game segment through Medal 2 inclusive, before its
competitive battles. Initial A/B is a separate sporting transition: fewer existing
authoritative adjusted deaths first, using the configured `division_sizes.A/B`.
Do not use wins or point sanctions, invent capacities, or distribute ordinary daily
points, coins, movement or gifts during the initial split. Preserve the 030/D death
calculation and the existing later daily competition behavior.

Only an equal-death block crossing the A/B cut requires an external decision.
Ties wholly within either division remain neutral. The boundary decision uses
existing admin authority, an explicit reason and exact current sporting inputs;
technical serialization order never determines membership. Changed progression,
deaths, roster or configuration invalidates an earlier review. Preserve typed
contracts, CAS, idempotency, safe unknown-outcome retries and historical rules.

Every required participant must have evidence of reaching the first-leg cap before
the split can become final. Missing evidence is unknown, not zero or ready. Until
cloud ingestion exists, absent save observations cannot enable the split. Neither
participants nor administrators may manually attest medals. Do not add a new Team
Lock prerequisite. Existing participant result
authority from C remains unchanged. Later game/postgame milestone decisions remain
outside E; no automatic progression beyond the approved evidence is inferred.

Owner decision (2026-10-01) resolves the entry question: only reliable save/parser
observations establish normal progress. Extend the neutral `ObservedSave` contract
with explicit badge evidence and game/region provenance. An observed zero remains
distinct from absent/unsupported progress. Show missing evidence as "Progreso no
observado / pendiente de sincronizar save". No self-attestation or routine admin
approval command is authorized. This includes the minimal progress foundation
needed by E, not full cloud ingestion or the final Launcher. Existing registered
badge counters alone are not observation evidence. No alternate manual death
counter or reinterpretation of existing seasons is authorized.

After implementation, complete the full relevant local matrix and any necessary
new migration/bootstrap parity before committing/pushing and public deployment.
Public verification uses safe reads and absent-resource checks, preserving all
manual owner data. The 2026-10-03 owner continuation authorizes F only after E is
fully green, committed, pushed, documented and coherently deployed, and only with
capacity to finish another atomic package. Otherwise stop at E's complete checkpoint.
Do not start G automatically or begin Phase 11.

## Approved championship decision for Package F (2026-10-01, clarified 2026-10-03)

E is closed; the 2026-10-03 continuation authorizes F, then STOP. The League
title uses final accumulated official total points, never the last daily snapshot.
Exactly two participants tied for the highest total play an external best of three:
the explicitly recorded and audited winner is champion. Previous League results
must not infer that winner. Exactly three tied for the highest total are ranked by
fewer authoritative adjusted deaths. If that does not identify a unique champion,
the title remains unresolved and requires explicit exceptional owner resolution.
No H2H, daily position, name, slug, UUID or insertion order can decide it.
These title rules are separate from D's daily ranking. Hall must use the resolved
championship result. Four-or-more top ties and any still-ambiguous finalist position
are not assigned an invented automatic rule by this decision.

Finalist may remain null with OWNER_DECISION_REQUIRED and does not block a proven
champion, finish or archive. Final-day close, finish and archive remain distinct:
finish freezes the proven title, accumulated exact points and historical public
Team Lock; archive consumes that certificate. Missing safe team history stays empty.
Old finished/archive history receives no automatic reinterpretation. Modern Cup
certification remains independent. Post-final League rewards are not generated by
finish/archive; broader shop repairs belong to I. See the [F report](phase10-5f-completion-report.md)
and live handoff for observed implementation/delivery state.

F is delivered as of 2026-10-03: source `6b46666`, migration
037=`20261003121543`, verified Railway/Cloudflare and preserved owner data. The
current instruction ends here; do not begin G automatically or start Phase 11.

## Authorized Package G continuation and closure (2026-10-05)

The subsequent explicit G instruction supersedes the historical stop-after-F note
for G only. G is now delivered: participants set their own live revived-after-wipe
counter through verified JWT ownership, strict nonnegative integers, CAS, stable
replay and transactional audit. The approved +2 adjusted deaths / -0.4 points per
Pokemon is unchanged, separately from purchased revives. Unknown observations and
frozen initial A/B, days, championship and Hall remain safe. GENERAL contains the
personal control; no Admin override or physical save write was added.

Final source `848e7b0`, forward 038=`20261004222029`, complete local closure,
Railway/Cloudflare and safe public read-only preservation are verified in the
[G report](phase10-5g-completion-report.md). Initial inherited browser stats schema
privileges were removed before delivery without changing RLS reads or owner data.
**STOP after G.** H requires the next explicit owner continuation; Phase 11 remains
NOT READY / NOT STARTED. Existing unresolved decisions below keep their scope.

## Owner decisions still required

Implement independent branches; never infer answers to these questions:

1. RESOLVED in I: default four coins per reliably observed badge, persistently configurable.
2. RESOLVED in I: default twelve coins once per season/challenge, persistently configurable.
3. RESOLVED in I: save proof of defeating the in-game Champion is required; eight badges and PokeApp finish/title are insufficient.
4. RESOLVED in J instruction and implemented in final alignment: normal OPEN/CLOSE/FINISH belongs to all eligible participants, preserving lifecycle, CAS and frozen history.
5. RESOLVED in J instruction: exactly two leaders use external deciding battle; 3+ use fewer authoritative adjusted deaths, then exceptional external owner/admin resolution if still tied. Finalist placement alone remains OWNER_DECISION_REQUIRED.
6. RESOLVED in I: purchased revive preserves one historical death (-0.2), without stacking it on the same still-visible death. G wipe revival remains two deaths (-0.4).
7. RESOLVED in J instruction: no replacement cutoff; lateness does not block a lock. Frozen historical locks remain immutable.
8. RESOLVED in K instruction: current permitted competitive Team Lock only, species/nickname/level/types/item/moves; no live save, party/boxes/dead-box/private identity fallback.
9. RESOLVED in J instruction: League DQ does not automatically exclude Cup.
10. RESOLVED general progression in L: badges → in-game Pokémon League → defeat Champion → game completed. Reliable save proof is required; eight badges alone and PokeApp competitive results are insufficient. Technical detection differs by format. Future per-round/postgame caps beyond the implemented J1 first-two-primary-badge rule are separate deferred roadmap configuration, not an unresolved general progression rule.

## Safety, evidence and completion

Preserve all owner manual seasons and Anto's current staging identity, PIN and
admin role. Never alter the active owner season to make a fixture runner pass.
Use disposable local PostgreSQL for active/destructive flows; safe isolated
staging fixtures or read-only public checks where required. Never read, inspect,
hash, stage or touch the protected guide named in the master protocol.

Existing applied migrations are immutable. Before new remote SQL verify the pinned
V2 project, actual migration history, committed source, fresh complete baseline
and Advisor inventory. Never replay 031/032, reset staging or change V1.
Reuse existing Railway and Cloudflare resources. Push source before deployment.

Focused checks cover affected API/domain/privacy, exact decimals, CAS/replay and
negative authorization; real local PostgreSQL for SQL, and React/build/browser
checks for changed screens. Record commands, source, results and limits in the
live handoff. Do not promote historical PASS or unverified remote state to VERIFIED.

Physical writes, cloud ingestion, installer/updater, PKForge/PKHeX overhaul,
Discord rebuild, V1 migration/cutover and final art/audio remain outside scope.
No progress credit for a contract alone. Full DONE needs all relevant FIX NOW
repairs, tests, coherent public delivery and clean/pushed Git. Use
`PHASE 10.5 PARTIAL — BLOCKED ONLY ON OWNER DECISIONS` only when no independent
implementation remains. Champion/Hall repair is a structural Phase 11 blocker.

## I delivery - 2026-10-07

I is DONE: exact economy balances, pending/active offers, owned reward vouchers,
post-League spending, configurable save-proven badge/Champion rewards and purchased
revive overlap. Basic reward controls are present; general Admin humanization stays
J. [Report and preserved-owner evidence](phase10-5i-completion-report.md).
No cloud ingestion or physical writes. STOP after I; J requires the next owner
instruction. Phase 10.5 remains IN PROGRESS; Phase 11 NOT READY / NOT STARTED.

## J authorized scope and resolved decisions - 2026-10-08

Historical J-scope record below. Its three backend gaps are superseded by the
final alignment implementation at the end of this document.

The explicit J instruction supersedes the historical stop-after-I note for J only.
J humanizes existing Admin controls, configuration and exceptional workflows;
it does not authorize a broad lifecycle/security or championship rewrite.
The resolved decisions above supersede older owner-decision entries; remaining
implementation gaps are not requests to decide those rules again:

- Normal OPEN/CLOSE/FINISH still requires admin in the API and shared SQL principal
  guards. Participant access needs a scoped authorization/API/SQL extension with
  eligibility, current-state, CAS, replay and concurrency coverage. Corrections and
  exceptional decisions retain separate admin authority.
- F's existing championship contract supports a two-player BO3 and exactly-three
  death comparison. Four-or-more leaders and residual death ties fail closed.
  Approved 3+ comparison and audited residual external resolution require a backend
  extension; J explains the gap and never decides the champion in React.
- Team Lock supports replacement during scheduled/open days and protects closed
  history. The current projection has overwritten `locked_at`, uninformative
  `is_late` and no usable deadline; it cannot prove first submission timing across
  cancellation/reopening. J displays Fijado/Pendiente only. Reliable timing needs
  first-submission/opening evidence, without introducing a replacement cutoff.
- League DQ has no automatic Cup DQ cascade. Existing lifecycle guards additionally
  block League exits while a linked Cup is draft/active; J explains that dependency.
  Later Cup admission does not filter League DQ. Cup logic is unchanged.

No migration or backend change is required by this scoped UI package. Delivery and
closure evidence belong in the live handoff. NEXT is K only after J closes and a
new owner instruction; Phase 11 remains NOT READY / NOT STARTED.


J is delivered as of 2026-10-08, source `49d4790`, Cloudflare only. Human controls,
current reward values, explicit confirmations and pending-command recovery are
verified; the scoped backend gaps above remain explicit. [J report](phase10-5j-completion-report.md).
**J scope ends here.** A separate owner instruction queues K after committed/pushed
J closure and entry verification. Phase 11 NOT READY.


## K contract - approved and implementing 2026-10-08

The queued K instruction is authorized only after J DONE verification; entry passed
at `37ac032`. Public scouting reuses H's season roster and current matchday pointer,
independently of scheduled matches. The server returns one selected public Team Lock
with an explicit six-field Pokemon allowlist and move names only. It omits PP/shiny
and timing fields rather than broadening the owner's list. Self/admin receive the
same public contract. Names/season/day/selection form the necessary navigation
context; no Pokemon identity/provenance data is returned.

No lock is null, never a fabricated empty team. No current day/roster is explicit;
no earlier-lock, save, PC or dead-box fallback. Existing frozen current-day locks
remain history. No eligibility/timing/sporting/Cup rule changes. The authenticated
read route rejects viewer/private/self/admin overrides. The React surface is reached
from Entrenadores and reads one aggregate endpoint per selection. Reuse H's query
bounds; cap overflow and malformed sources fail closed. Real local PG verifies
existing projection/RLS/grants and historical independence; no migration/rebuild.

K's public scouting scope supersedes stale unresolved-scope wording in dated reports.
No broader publication beyond this competitive snapshot is inferred. Stop after K;
L and Phase 11 require separate authorization.


K delivered 2026-10-08, source `23081e1`, Railway then Cloudflare. No migration;
56 scoped tables and all 31 migration records preserved. Public missing-state and
privacy/auth checks pass; positive six-Pokemon proof is local only because sampled
hosted locks are absent. [K report](phase10-5k-completion-report.md).
**STOP after K. NEXT L requires a new owner instruction.** Phase 11 NOT READY.

## Package L delivered (2026-10-08)

L is DONE after verified K entry and explicit owner authorization. E/I progress,
completion detection and rewards were already satisfied and remain unchanged.
040 adds a private current-observation read; API/React now expose regional medals
and in-game Champion true/false/unknown without default-counter inference or manual
attestation. [Report and evidence](phase10-5l-completion-report.md).
Full cloud ingestion remains unfinished; current save observations cannot rewrite
competitive history. The three J implementation gaps retain their existing scope.
**STOP after L. NEXT M requires its own instruction.** Phase 11 NOT READY.

## Final product alignment - delivered (2026-10-08)

The explicit final instruction supersedes previous package stopping points for
this closure only. A–M and the seven final areas are verified locally and deployed.
Remote completion and owner preservation are recorded in the final report/handoff.

- Admin edits current badge/Champion reward amounts directly. A server-side
  immutable revision takes effect for subsequently accepted eligible observation
  events; old claims, ledger entries and frozen history never change. Client save
  timestamps cannot backdate the cutover. Zero remains valid. Structural format
  changes stay restricted to unused draft configuration, without future-version UI.
- Commands invalidate affected reads for their viewer and season. Active affected
  screens refresh immediately; inactive reads are stale for the next visit. CAS
  conflict refresh is automatic, while a new intent still requires user review.
  Unknown outcomes retain exact original bodies/keys, including after failed reads.
- Trainer cards open visual profiles. Rival teams use K's public six-field
  projection only; self details reuse H and own Mi PC. No cloud save means no
  invented team, PC, medal or death observation. Shop uses the four authoritative
  item categories; M's lazy trainer-name lookup and I's economic rules remain.
- Enabled active eligible participants may open/close the current League day and
  finish a proven completed season through verified API/SQL authority. Daily tie
  decisions, corrections, championship exceptions, archive and configuration stay
  admin-only. Normal close cannot submit a tie override. League DQ does not cascade
  to Cup; existing linked-Cup exit protection remains unchanged.
- Championship supports 3+ tied leaders, including 4+, by minimum frozen adjusted
  deaths. Remaining tied candidates require an explicit audited admin external
  decision with reason and current source fingerprint. Two-player BO3 is retained.
  Missing death evidence stays unresolved. React never chooses sporting winners.
- New first-fixation and first-start evidence proves Team Lock on-time/late status.
  Replacement, cancellation and reopening preserve those first events. No cutoff
  is introduced during editable days. Old locks without proof show unknown timing;
  no historical timing is fabricated. Public status reveals no private Pokémon data.

Forward 041 implements the minimal persistent evidence and guards; earlier SQL,
certified seasons, snapshots, Hall and Cup remain unchanged. General progression,
badge/Champion economics, public scouting, League-only DQ, participant authority,
championship residual policy and no Team Lock cutoff are resolved decisions.
Finalist policy remains separately undefined and does not prevent a proven title.
Full cloud ingestion, physical save writes and broader Phase 14 work remain deferred.
041=`20261008204133`, final application source `eb4e402`, compatible Railway and
Cloudflare delivery verified. Phase 11 is READY FOR REVIEW, NOT STARTED, and must
wait for explicit review/authorization. Known M availability work remains deferred.
