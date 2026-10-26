# Save engine — physical protocol, artifacts and recovery (26D)

Source: `app/launcher/write_engine.py` (`no_replace_v1`), `write_files.py`,
`handoff_files.py`. The SQLite journal in the Launcher profile is the single
persistent source of physical truth; nothing is decided from file names or ages.

## Sequence of one write

1. **Authorize + locks** — profile lock `physical-write.lock` (inside the
   profile) and save lock `.pokeapp-write-<hash>.lock` beside the save, both
   opened exclusively (share mode 0). Exclusivity is the open handle; since 26D
   the save lock is deleted with its last handle (`FILE_FLAG_DELETE_ON_CLOSE`).
   Emulator processes (lime3ds, lime-qt, azahar, citra, …) refuse the write.
2. **Prepare** — journal record; verified, read-only **backup of the original
   in the profile** (`write-backups/`), and a verified `.pokeapp-<op>.stage`
   (the native output) beside the save.
3. **Confirm (handoff)** — journal `commit_started`; park the original as
   `.pokeapp-<op>.displaced` (rename by handle, never replaces); publish the stage
   as `main`; independent native verification; journal `APPLIED_VERIFIED`.
4. **26D retirement** — journal `residue=REMOVAL_INTENT`, then the parked copy is
   deleted **by handle** only if it is the journal's recorded file identity, its
   bytes equal the original and the profile backup is verified; then
   `residue=REMOVED`. Any doubt keeps it (`KEPT_CHANGED` or `KEPT_<reason>`).
5. **Restore** (user-initiated, verified backups only) — before-restore backup of
   the current output, `.restore` stage published, applied output parked as
   `.restored-output`, later retired the same way (`restore_residue`).

## Artifacts

| Artifact | Where | Purpose | Removed when |
| --- | --- | --- | --- |
| original / before-restore backup | profile `write-backups/` | transactional recovery | original only, by the daily policy below; before-restore never |
| daily point `<date>.sav` + `.json` | profile `daily-backups/<save key>/` | state before the day's first write | recognized and older than 30 days, never the newest |
| `.pokeapp-<op>.stage` | beside save | active publication input | consumed by the publish rename |
| `.pokeapp-<op>.displaced` | beside save | proof of which original was parked during a commit | terminal verified + identity + bytes + backup verified |
| `.pokeapp-<op>.restored-output` | beside save | parked applied output during restore | same rule against the before-restore backup |
| `.pokeapp-write-<hash>.lock` | beside save | cross-process exclusion | with its last handle |
| any other file | — | emulator/user/unknown | **never touched** |

The parked copy must stay beside the save while a commit is uncertain: it is the
renamed original (same volume, atomic rename), and moving it across volumes
would break that proof. After verification the profile backup is the recovery.

## Interruptions and outcomes

| Interruption | Outcome after restart (reconcile) |
| --- | --- |
| before backup / after backup / before park | not applied (`REJECTED`, original intact) |
| after park, before publish | recovery required; the parked original is proven by identity and bytes |
| after publish / before or after verify | `APPLIED_VERIFIED` once (never re-applied) |
| before or during retirement | retirement completed or the copy kept; status unchanged |
| lost reply, restart, second Launcher | same operation id reconciled; a held lock refuses (`WRITE_ALREADY_RUNNING`) |
| file edited or restored externally | refused/preserved (`SOURCE_HASH_CHANGED`, `EXTERNAL_CHANGE_PRESERVED`) |
| corrupt backup | restore refused (`RECOVERY_REQUIRED`), file untouched |
| two-save robbery leg | no unilateral restore (`TRANSFER_COORDINATED_RECOVERY_REQUIRED`) |

Power loss is not the same as killing the process (tested); it is PENDING.

## Daily retention (owner decision 2026-10-26)

One ordinary restore point per save and local date, kept 30 days, replaces one
permanent copy per write. Runs after every verified apply (`_apply_retention`):

1. The transactional backup is still created and verified before every write.
2. If the save has no point for today, the operation's verified pre-write bytes
   become `<YYYY-MM-DD>.sav` with a manifest (`date`, `target`, `game`,
   `trainer_key`, `sha256`, `size`, `operation_id`). Exclusive create, read-only,
   never overwritten by later writes that day.
3. Older transactional backups of the same save are retired only when **all**
   hold: no operation on that save is pending (`PREPARED`, `AWAITING_CONFIRMATION`,
   `RECOVERY_REQUIRED`); the record is `APPLIED_VERIFIED` under this policy
   (`retention=daily_v1`), its beside-save copy is `REMOVED`, it was never
   restored, it is not a robbery leg, its day has a recognized point, and its
   bytes still verify. Journal `backup_retired=INTENT` first, then `RETIRED`; an
   interrupted retirement is completed by the next write.
4. Recognized points 30 or more days old are deleted, never the newest one.

Never touched: the latest write's backup, failed/pending/uncertain/restored
records, robbery legs, every backup from before the policy (no purge on
activation), files in `daily-backups/` without a matching manifest and bytes, and
transactional backups changed outside PokeApp. Any error keeps everything and
records `retention_error`.

A retired record stays terminal history: `reconcile` only compares the current
file, and `restore` refuses with `BACKUP_RETIRED_USE_DAILY_POINT` (its state was
not restorable anyway once a newer write replaced the file). The Launcher lists
each point as «Copia diaria del <fecha>» with the game and «Guardar copia…»
(verified export, `role=daily`); the latest write keeps «Restaurar copia…».

