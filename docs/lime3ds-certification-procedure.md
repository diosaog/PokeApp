# Lime3DS certification procedure (disposable copy)

Prepared in Phase25B for the next acceptance step. **Never modify the owner's
original save.** Every step below works on a copy, and the owner must confirm
the exact source path and the scope before step 3.

1. **Detect.** Owner opens Lime3DS once and closes it. In the Launcher press
   «Buscar partidas en Lime3DS, Azahar o Citra». Record emulator, title and path
   shown (expected under `%APPDATA%\Lime3DS\sdmc\Nintendo 3DS\…\00055e00\…\main`
   for Pokémon Y). With Lime3DS running, any change must be refused
   (`EMULATOR_RUNNING`).
2. **Owner confirmation.** Owner states in writing: exact path, that a copy may
   be made, and which operations may run on the COPY (Rare Candy, Heart Scale;
   no robbery or revive on the three personal Pokémon).
3. **Copy and verify.** With Lime3DS closed, copy the original to an
   independent backup folder outside the emulator directories; record SHA-256 of
   original and copy (must match). Make a second working copy. Prove the backup
   restores byte-identically to a scratch location.
4. **Work only on the working copy** placed where Lime3DS can load it (a
   separate test title folder or a separate Lime3DS user directory), never by
   overwriting the original. Read it in the Launcher; record the trainer, three
   Pokémon and the Rare Candy/Heart Scale counts.
5. **Rare Candy.** Type a quantity, adjust with + and −, «Añadir», confirm with
   the emulator closed. Verify backup created, native readback count, and that
   Pokémon, money, progress and other items are unchanged.
6. **In game.** Open the copy in Lime3DS, check the bag visually, save in game,
   close, reopen, check again. Re-read in the Launcher. Only this step is an
   in-game PASS; a parser PASS alone is not.
7. **Heart Scale.** Repeat 5–6. Also: maximum quantity, emulator open, lost
   reply (close the Launcher during confirmation and reopen: it must reconcile,
   never add twice). Gen7 note: Y is Gen6 and has no MemeCrypto signature.
8. **Recovery.** On another disposable copy: externally modified file before
   confirm (must refuse), interruption before/after write, restart with a
   pending journal, verified restore of the original backup.
9. **Record** results per step with hashes and screenshots; keep backups. Two-
   save robbery cannot be certified with one personal save; revive needs a
   prepared Box 8 copy, never one of the three personal Pokémon.
