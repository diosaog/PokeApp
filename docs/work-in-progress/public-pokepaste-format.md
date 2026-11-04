# Public Pokepast.es format verification — 2026-11-04

Status: PUBLISHED 2026-11-04; API deployment and HTTP acceptance verified.
Original branch `codex/public-pokepaste-format`,
from `16708e9` (`claude/all-vs-all-league-start`, matched against origin
with `git ls-remote`). Separate fix commit `c2e8617`, preserved in
`codex/mid-season-enrollment`. The owner subsequently authorized SQL 080,
API and web; the API includes this fix. Existing untracked owner files are
excluded; no new external paste was created.

Published API: `adfca5c4-fb5e-4739-a239-b08ccfbb92c2` SUCCESS, source
`6490e3de84c575a771348c26c9fe0d0544aa6b14`, 2026-11-04 15:37 UTC.
Health 200 / OpenAPI 132 routes. Migration 080 and the web belong to the
enrollment feature; the transport correction itself needs neither.
[Combined release evidence, authorization and rollback](mid-season-enrollment.md).

Continuity: [MultiIA protocol](../AI/PokeApp_Multi_AI_Continuity_Protocol.md),
[checkpoint](../project-checkpoint.md),
[published 079 release](all-vs-all-league-start.md),
[public paste contract](ux-showdown-matchdays-live.md).

## Verified findings

- Production uses `app/application/announcements.py` → public projection of
  `app/domain/showdown.py` → `app/application/pokepaste.py`. The legacy
  `app/entrenadores/pokepaste.py` is not this path.
- The outbox reads `public_team_snapshot`, never the private snapshot or
  mutable party. Name resolution already uses the generated Showdown tables.
- The upstream v3 renderer splits sets on CRLF CRLF and lines on CRLF;
  its create/storage code does not normalize line endings. Our serializer
  emits LF, and httpx form encoding preserves those bytes.
- Read-only GET of the previously authorized synthetic paste
  `https://pokepast.es/7a00cfd5f754cb45`: 35 LF, zero CRLF; HTML has one
  article, `/img/pokemon/0-0.png`, no item image. No new paste was created.
- Upstream move lookup uses exact English table keys. Official Spanish
  names such as Terremoto, Lanzallamas and Rayo are absent. Keep English.
- Some valid Showdown forms/moves/items are missing or differently named in
  Pokepast.es itself. Do not replace a correct identity with another form
  or promise unsupported artwork.

## Correction and preserved behavior

`Pokepaste.create` normalizes LF/CR/CRLF to CRLF before validating and
encoding the existing form. This is the only runtime behavior changed.
The public serializer already matches the example's names, nicknames,
items, moves and blank-line structure; no name-table or private-export
change was needed. The outbox, URL validation/storage, retry budget,
uncertain-delivery handling and replacement edits remain as implemented.
Existing stored URLs are reused, never automatically regenerated.

## Validation

Windows / `.venv-api`, base `16708e9`:

- `tools/run_unit_tests.py --pattern test_public_team_pastes.py`: 19 PASS.
- `tools/run_unit_tests.py --pattern test_showdown_export.py`: 26 PASS.
- After the fix: `tools/run_unit_tests.py --pattern test_public_team_pastes.py`:
  **24 PASS**, including the exact example at the real HTTP-form boundary
  (mocked), four moves in each of six sets, form/gender/missing-item names,
  public field allowlist, mutable-party isolation, strict response URLs,
  bounded retries, no duplicate announcements and replacement URL/message edits.
- The new wire-format tests failed before the runtime correction (one set
  instead of six). An initially invalid Pyroar form-index fixture was
  corrected to form 0 plus public gender F, matching the parser contract.
- `python -m unittest discover -s tests -p test_gender_pipeline.py`:
  **4 PASS**. Private Showdown compatibility includes the existing PKHeX
  reference-party test, real IVs, EVs fixed to 1 and Hidden Power privacy.
- `python -m compileall -q app tests`: exit 0.
- `ruff check app/application/pokepaste.py tests/test_public_team_pastes.py
  --ignore C408`: exit 0. Unfiltered lint retains the same **10 C408**
  findings in the pre-existing test harness (`dict(...)` style); no new
  findings. Two pre-existing import-order findings were corrected in touched files.
- Initial whole tracked suite: 1484 tests, 3 subprocess-import failures in
  `test_phase22c_handoff` because the child Python processes did not inherit
  the tests directory in PYTHONPATH. Final run supplies repository + tests
  in PYTHONPATH, using the existing isolated runner with tracked-only module
  discovery (124 modules); unrelated untracked owner tests are excluded.
- Final whole tracked suite: **1484 PASS, zero failures/errors/skips,
  157.543 seconds, exit 0**. This includes League start, player matchdays,
  Team Lock/API/announcements, session-security, scoring/economy/history
  and Launcher save-protection regressions. No runtime/test-harness fix
  outside the paste tests was made.
- `git diff --check` for all staged paths: exit 0. Report/checkpoint links
  and the structured evidence JSON validate. All observations above are
  2026-11-04 on base `16708e9` plus the changes in this commit.
- An initial direct `unittest` invocation failed importing
  `phase9_fixtures`; the repository runner supplies the correct discovery
  path and passes. This was an invocation issue, not a product failure.

Temporary upstream source/GET evidence:
`%TEMP%/pokeapp-pokepaste-audit-msmbsj_b`; no real player data.

## Renderer and visual evidence

[Structured verification](../evidence/public-pokepaste-format/verification.json),
[visually inspected screenshot](../evidence/public-pokepaste-format/example-local.png).

Pinned upstream: `felixphew/pokepaste` v3 commit
`617fd20ebb1b3bf0a059e68247c6266fea49db90`.
Original `syntax.go`, `data.go` and `paste.tmpl` were downloaded into the
temporary audit directory. Only the package declaration was changed to
`main`; a stdin + `httptest.ResponseRecorder` wrapper calls `renderPaste`.
`go build -o renderer.exe syntax.go data.go main.go` uses a portable Go
1.27.3 compiler (official archive SHA-256 verified). No database or server
is involved. Input is the actual decoded form captured with
`httpx.MockTransport`, serialized from `EXAMPLE_TEAM` in the public tests.

- Original LF input: **1 article, unknown 0-0 image, 0 item icons, 0 colored moves**.
- Corrected wire input: **6 articles, 6 correct Pokémon images, 6 correct
  item icons, 24 colored moves**. Includes the public level line as allowed.
- Form input: distinct `Meowstic` / `Meowstic-F` images (`678-0` / `678-1`),
  `Nidoran-F` / `Nidoran-M`, `Rotom-Wash`; all six image assets loaded.
- English Thunderbolt/Earthquake/Flamethrower: **3 colored moves**;
  official Spanish Rayo/Terremoto/Lanzallamas: **0**. Keep English.
- Playwright + installed Chrome (the bundled browser was unavailable):
  the local HTML was fulfilled in an intercepted request; original CSS and
  images loaded with GET. All non-GET browser requests were blocked.
  Screenshot inspected at 1440 × 1100; all 12 example images loaded.

This verifies local rendering with the upstream renderer and live assets,
not a new hosted paste or a post-deployment Discord delivery.

## Third-party limits

All 807 base species names match upstream keys. Some valid Showdown forms
are absent (e.g. Furfrou trims, Unown letters, several Pikachu hats);
Vivillon-Icy Snow/High Plains have different upstream spelling. Pyroar F
remains correctly identified in text, but upstream ignores cosmetic gender
for its artwork (`668-0`). Vise Grip, Conversion 2 and some item icons also
have upstream gaps. Preserve correct identities; do not guess alternative
species/forms, invent names or promise unsupported sprites/icons.

## Published state and remaining evidence limit

The focused implementation, tests and evidence were committed as `c2e8617`.
They are published within the combined release above; continue from the tip
of `origin/codex/mid-season-enrollment`. New legitimate Team Lock pastes
use the corrected CRLF transport; existing stored links remain untouched.
The upstream-renderer result remains local evidence. A new hosted paste and
post-deployment Discord delivery were not tested artificially; their first
real delivery remains an observation for legitimate user activity.

Rollback uses the previous API source `f2f799c` / deployment `ef13a7ce`
(now REMOVED after replacement), as detailed in the enrollment record.
No public POSTs, Discord sends or real save operations were performed for
this verification. The protected product guide was not
read, searched, hashed, changed, moved or staged. Other owner work remains
excluded. The combined release separately validates 080 and the hosted API/web.
All audit/test/compiler/browser processes started for this work completed;
the browser was closed. Synthetic scratch files and raw logs remain only
in the temporary audit directory noted above.

Remote DB/API/web were verified in the combined release. Its exact remote
state is `VALIDATION_PARTIAL`: technical checks passed, authenticated preview
and first real enrollment/delivery remain pending legitimate sessions.
