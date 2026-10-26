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
| original / before-restore backup | profile `write-backups/` | permanent recovery | never automatically (no approved policy) |
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
