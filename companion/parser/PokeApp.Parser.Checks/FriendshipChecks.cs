using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;
using System.Text.Json.Nodes;

// «Felicidad máxima» on in-memory copies of the retained public contributor
// fixtures (never a player's save). A deliberately randomized party: a species
// with moves it cannot learn, a traded Pokémon held by another handler, one
// already at 255 and an egg. Since 2026-11-12 also the PC: a Pokémon in Box 1,
// a traded one in the last box's last slot, an empty slot and a boxed egg.
// Proves the exact byte change in place (nothing moves) and every refusal.
internal static class FriendshipChecks
{
    private static int checks;
    private static void Check(bool value, string label)
    {
        if (!value) throw new Exception(label);
        checks++;
    }
    private static JsonObject Node(object value) => JsonSerializer.SerializeToNode(value, Inspection.Json)!.AsObject();
    private static JsonObject Execute(JsonObject request, bool verify = false)
        => Node(NativeWrite.Execute(JsonSerializer.SerializeToUtf8Bytes(request), verify));
    private static string? Error(JsonObject response) => response["error"]?.GetValue<string>();

    private static PKM Member(SaveFile save, ushort species, byte form, uint pid, string nickname)
    {
        var p = TrainingChecks.Specimen(save);
        p.Species = species; p.Form = form; p.PID = pid; p.EncryptionConstant = pid ^ 0x5A5A5A5A;
        p.Nickname = nickname; p.IsNicknamed = true;
        // Randomized: moves this species never learns, as in the League's saves.
        p.Move1 = 221; p.Move2 = 14; p.Move3 = 87; p.Move4 = 394;
        p.ResetPartyStats(); p.Stat_HPCurrent = 9;
        return p;
    }

    private static JsonObject Request(byte[] source, int slot, Func<JsonObject, JsonObject>? edit = null)
    {
        var save = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
        var p = save.GetPartySlotAtIndex(slot);
        var request = new JsonObject
        {
            ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(source),
            ["intent"] = new JsonObject
            {
                ["game"] = save.Version.ToString(), ["expected_sha256"] = NativeWrite.Hash(source),
                ["trainer_key"] = NativeWrite.TrainerKey(save),
                ["mutation"] = new JsonObject
                {
                    ["kind"] = "max_friendship", ["location"] = "party", ["slot_index"] = slot,
                    ["expected_pokemon_sha256"] = NativeWrite.Hash(p.DecryptedBoxData),
                    ["expected_friendship"] = (int)p.CurrentFriendship,
                },
            },
        };
        return edit is null ? request : edit(request);
    }

    private static JsonObject BoxRequest(byte[] source, int box, int slot, Func<JsonObject, JsonObject>? edit = null)
    {
        var save = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
        var p = save.GetBoxSlotAtIndex(box, slot);
        var request = Request(source, 0);
        request["intent"]!["mutation"] = new JsonObject
        {
            ["kind"] = "max_friendship", ["location"] = "box", ["box_index"] = box, ["slot_index"] = slot,
            ["expected_pokemon_sha256"] = NativeWrite.Hash(p.DecryptedBoxData),
            ["expected_friendship"] = (int)p.CurrentFriendship,
        };
        return edit is null ? request : edit(request);
    }

    // Raw stored write, as the game keeps a boxed Pokémon (no import helper).
    private static void PutBox(SaveFile save, PKM? p, int box, int slot)
        => save.WriteBoxSlot(p ?? save.BlankPKM, save.Data.AsSpan(save.GetBoxSlotOffset(box, slot), 232));

    private static byte[] Write(SaveFile save) => (byte[])typeof(TrainingChecks).GetMethod("WriteFixture",
        System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)!.Invoke(null, new object[] { save })!;

    private static void Reject(JsonObject request, string code, string label, bool verify = false)
    {
        var response = Execute(request, verify);
        Check(response["status"]!.GetValue<string>() == "rejected" && response["output_base64"] is null
              && Error(response) == code, label + ": " + Error(response));
    }

    public static void Run(string fixtureRoot, string outputRoot)
    {
        Directory.CreateDirectory(outputRoot);
        var report = new List<object>();
        foreach (string game in new[] { "X", "Y", "OR", "AS", "SN", "MN", "US", "UM" })
        {
            var contributor = File.ReadAllBytes(Path.Combine(fixtureRoot, game, "prepared"));
            var derived = SaveUtil.GetVariantSAV((byte[])contributor.Clone())!;
            Check(derived.Version.ToString() == game, game + " fixture game");

            var own = Member(derived, 711, 2, 0x11111111, "Jalowin");          // OT-held, Large size
            own.CurrentHandler = 0;
            own.OriginalTrainerFriendship = 70; own.HandlingTrainerFriendship = 9;
            ((IAffection)own).OriginalTrainerAffection = 40; ((IAffection)own).HandlingTrainerAffection = 3;
            var traded = Member(derived, 445, 0, 0x22222222, "Tiburon");      // received in a trade
            traded.OriginalTrainerName = "Otro"; traded.TID16 = (ushort)(derived.TID16 ^ 0x5555);
            traded.HandlingTrainerName = derived.OT; traded.HandlingTrainerGender = derived.Gender; traded.CurrentHandler = 1;
            traded.OriginalTrainerFriendship = 120; traded.HandlingTrainerFriendship = 30;
            ((IAffection)traded).OriginalTrainerAffection = 7; ((IAffection)traded).HandlingTrainerAffection = 12;
            var full = Member(derived, 25, 0, 0x33333333, "Lleno");
            full.CurrentHandler = 0; full.OriginalTrainerFriendship = 255;
            var egg = Member(derived, 175, 0, 0x44444444, "Huevo");
            egg.IsEgg = true; egg.OriginalTrainerFriendship = 10;
            foreach (var p in new[] { own, traded, full, egg }) p.RefreshChecksum();
            derived.PartyData = [own, traded, full, egg];
            // The PC: Box 1 slot 1, an empty Box 1 slot 2, a boxed egg and a
            // traded Pokémon (handler friendship) in the very last box slot.
            int lastBox = derived.BoxCount - 1;
            var boxed = Member(derived, 448, 0, 0x55555555, "Caja");
            boxed.CurrentHandler = 0; boxed.OriginalTrainerFriendship = 50; boxed.HandlingTrainerFriendship = 4;
            ((IAffection)boxed).OriginalTrainerAffection = 20; ((IAffection)boxed).HandlingTrainerAffection = 2;
            boxed.HeldItem = 234; boxed.EV_SPA = 252; boxed.IV_SPE = 31; boxed.Nature = Nature.Timid;
            var far = Member(derived, 149, 0, 0x66666666, "Lejos");
            far.OriginalTrainerName = "Otra"; far.TID16 = (ushort)(derived.TID16 ^ 0x3333);
            far.HandlingTrainerName = derived.OT; far.HandlingTrainerGender = derived.Gender; far.CurrentHandler = 1;
            far.OriginalTrainerFriendship = 200; far.HandlingTrainerFriendship = 33;
            var boxEgg = Member(derived, 175, 0, 0x77777777, "Huevo");
            boxEgg.IsEgg = true; boxEgg.OriginalTrainerFriendship = 10;
            foreach (var p in new[] { boxed, far, boxEgg }) p.RefreshChecksum();
            PutBox(derived, boxed, 0, 0); PutBox(derived, null, 0, 1); PutBox(derived, null, 0, 2);
            PutBox(derived, boxEgg, 1, 5); PutBox(derived, far, lastBox, 29);
            var source = (byte[])typeof(TrainingChecks).GetMethod("WriteFixture",
                System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)!
                .Invoke(null, new object[] { derived })!;
            Check(Node(Inspection.Inspect(source))["error"] is null, game + " disposable source valid");

            // The fixed offsets are PKHeX's own fields: OT 0xCA, handler 0xA2; affection beside them.
            var parsed = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
            var p0 = parsed.GetPartySlotAtIndex(0); var p1 = parsed.GetPartySlotAtIndex(1);
            Check(p0.Data[0xCA] == 70 && p0.Data[0xA2] == 9 && p0.Data[0xCB] == 40 && p0.Data[0xA3] == 3
                  && p0.CurrentFriendship == 70, game + " OT friendship and affection offsets");
            // PKHeX's import re-derives a traded slot's handler friendship; the save keeps whatever it set.
            int handled = p1.Data[0xA2];
            Check(p1.CurrentHandler == 1 && p1.Data[0xCA] == 120 && handled != 120 && p1.CurrentFriendship == handled,
                  game + " a traded Pokémon's game friendship is the handler's byte, not the OT's");

            var inspected = Node(NativeFriendship.Inspect(JsonSerializer.SerializeToUtf8Bytes(new JsonObject
                { ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(source) })));
            var party = inspected["semantic_diff"]!["party"]!.AsArray();
            Check(inspected["status"]!.GetValue<string>() == "inspected" && inspected["output_base64"] is null
                  && party.Count == 4, game + " party inspection: " + Error(inspected));
            Check(party.Select(e => e!["friendship"]!.GetValue<int>()).SequenceEqual([70, handled, 255, 0])
                  && party.Select(e => e!["eligible"]!.GetValue<bool>()).SequenceEqual([true, true, true, false])
                  && party[0]!["species"]!.GetValue<int>() == 711 && party[0]!["form"]!.GetValue<int>() == 2
                  && party[0]!["nickname"]!.GetValue<string>() == "Jalowin",
                  game + " current friendship per member; eggs are not eligible");
            var boxes = inspected["semantic_diff"]!["boxes"]!.AsArray();
            JsonNode? At(int b, int s) => boxes.FirstOrDefault(e =>
                e!["box_index"]!.GetValue<int>() == b && e!["slot_index"]!.GetValue<int>() == s);
            var keys = boxes.Select(e => e!["box_index"]!.GetValue<int>() * 30 + e!["slot_index"]!.GetValue<int>()).ToArray();
            int occupied = Enumerable.Range(0, parsed.BoxCount)
                .Sum(b => Enumerable.Range(0, 30).Count(s => parsed.GetBoxSlotAtIndex(b, s).Species != 0));
            Check(keys.Zip(keys.Skip(1)).All(k => k.First < k.Second) && keys.Length == occupied
                  && boxes.All(e => e!["species"]!.GetValue<int>() != 0),
                  game + " every occupied slot of every box is listed once, in order; empty slots are not");
            Check(At(0, 0)?["friendship"]!.GetValue<int>() == 50 && At(0, 0)!["eligible"]!.GetValue<bool>()
                  && At(0, 0)!["species"]!.GetValue<int>() == 448 && At(0, 0)!["nickname"]!.GetValue<string>() == "Caja"
                  && At(0, 1) is null && At(1, 5)?["eligible"]!.GetValue<bool>() == false
                  && At(lastBox, 29)?["friendship"]!.GetValue<int>() == 33 && At(lastBox, 29)!["eligible"]!.GetValue<bool>(),
                  game + " Box 1, the last box, an empty slot and a boxed egg read correctly");

            foreach (int slot in new[] { 0, 1 })
            {
                var request = Request(source, slot);
                var response = Execute(request);
                Check(response["status"]!.GetValue<string>() == "prepared", game + " slot " + slot + " prepared: " + Error(response));
                var output = Convert.FromBase64String(response["output_base64"]!.GetValue<string>());
                var verify = request.DeepClone().AsObject();
                verify["output_base64"] = Convert.ToBase64String(output);
                Check(Execute(verify, true)["status"]!.GetValue<string>() == "verified", game + " slot " + slot + " independent verify");

                var after = SaveUtil.GetVariantSAV((byte[])output.Clone())!;
                var before = parsed.GetPartySlotAtIndex(slot);
                var changed = after.GetPartySlotAtIndex(slot);
                int field = slot == 0 ? 0xCA : 0xA2;
                Check(changed.CurrentFriendship == 255 && changed.ChecksumValid, game + " slot " + slot + " friendship 255");
                var differing = Enumerable.Range(0, before.Data.Length).Where(i => before.Data[i] != changed.Data[i]).ToArray();
                Check(differing.All(i => i == field || i is 6 or 7) && differing.Contains(field),
                      game + " slot " + slot + " only the game's friendship byte (+checksum) changed");
                Check(changed.Data[0xCB] == before.Data[0xCB] && changed.Data[0xA3] == before.Data[0xA3]
                      && changed.Data[slot == 0 ? 0xA2 : 0xCA] == before.Data[slot == 0 ? 0xA2 : 0xCA],
                      game + " slot " + slot + " Amie affection and the other friendship untouched");
                Check(changed.Species == before.Species && changed.Form == before.Form && changed.PID == before.PID
                      && changed.EncryptionConstant == before.EncryptionConstant && changed.Move1 == 221 && changed.Move4 == 394
                      && changed.Stat_HPCurrent == before.Stat_HPCurrent && changed.Status_Condition == before.Status_Condition,
                      game + " slot " + slot + " identity, randomized moves, HP and status preserved");
                Check(Enumerable.Range(0, 4).Where(i => i != slot).All(i =>
                          parsed.GetPartySlotAtIndex(i).Data.AsSpan().SequenceEqual(after.GetPartySlotAtIndex(i).Data))
                      && Enumerable.Range(0, parsed.BoxCount).All(b => Enumerable.Range(0, parsed.BoxSlotCount).All(s =>
                          parsed.GetBoxSlotAtIndex(b, s).Data.AsSpan().SequenceEqual(after.GetBoxSlotAtIndex(b, s).Data))),
                      game + " slot " + slot + " every other party member and every box unchanged");
                Check(after is not SAV7 || NativeSignature.VerifySave(output), game + " slot " + slot + " signature valid");
                if (slot == 0)
                {
                    // Repeating on 255 is a harmless refusal: no new bytes.
                    Reject(Request(output, 0), "FRIENDSHIP_ALREADY_MAX", game + " repeat on 255");
                    if (game == "Y")
                    {
                        File.WriteAllBytes(Path.Combine(outputRoot, "Y-source.sav"), source);
                        File.WriteAllBytes(Path.Combine(outputRoot, "Y-output.sav"), output);
                    }
                }
                // A forged output that also touches affection is refused by the verifier.
                var forged = SaveUtil.GetVariantSAV((byte[])output.Clone())!;
                var tampered = forged.GetPartySlotAtIndex(slot);
                tampered.Data[0xCB] ^= 1; tampered.RefreshChecksum();
                forged.WritePartySlot(tampered, forged.Data.AsSpan(forged.GetPartyOffset(slot), 260));
                var bad = request.DeepClone().AsObject();
                bad["output_base64"] = Convert.ToBase64String((byte[])typeof(TrainingChecks).GetMethod("WriteFixture",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)!.Invoke(null, new object[] { forged })!);
                Check(Execute(bad, true)["status"]!.GetValue<string>() == "rejected", game + " forged affection change refused");
            }
            Reject(Request(source, 2), "FRIENDSHIP_ALREADY_MAX", game + " already at 255");
            Reject(Request(source, 3), "UNSAFE_TARGET", game + " egg");
            Reject(Request(source, 0, r => { r["intent"]!["mutation"]!["expected_friendship"] = 71; return r; }),
                   "STALE_MUTATION", game + " friendship changed since shown");
            Reject(Request(source, 0, r => { r["intent"]!["mutation"]!["expected_pokemon_sha256"] = new string('0', 64); return r; }),
                   "STALE_MUTATION", game + " another Pokémon in that slot");
            Reject(Request(source, 0, r => { r["intent"]!["expected_sha256"] = new string('0', 64); return r; }),
                   "STALE_SOURCE", game + " save changed since read");
            Reject(Request(source, 0, r => { r["intent"]!["trainer_key"] = new string('0', 64); return r; }),
                   "WRONG_TRAINER", game + " another trainer's save");
            Reject(Request(source, 5, r => r), "UNSAFE_TARGET", game + " empty party slot");

            // ---- PC boxes: the Pokémon changes where it is; nothing else moves ----
            int sigStart = parsed is SAV7USUM ? 0x6C000 + MemeCrypto.SaveFileSignatureOffset
                : parsed is SAV7SM ? 0x6BA00 + MemeCrypto.SaveFileSignatureOffset : -1;
            foreach (var (box, slot, field) in new[] { (0, 0, 0xCA), (lastBox, 29, 0xA2) })
            {
                string label = game + " box " + (box + 1) + " slot " + (slot + 1);
                var request = BoxRequest(source, box, slot);
                var response = Execute(request);
                Check(response["status"]!.GetValue<string>() == "prepared", label + " prepared: " + Error(response));
                var diff = response["semantic_diff"]!.AsObject();
                Check(diff["location"]!.GetValue<string>() == "box" && diff["box_index"]!.GetValue<int>() == box
                      && diff["slot_index"]!.GetValue<int>() == slot, label + " receipt names the box and slot");
                var output = Convert.FromBase64String(response["output_base64"]!.GetValue<string>());
                var verify = request.DeepClone().AsObject();
                verify["output_base64"] = Convert.ToBase64String(output);
                Check(Execute(verify, true)["status"]!.GetValue<string>() == "verified", label + " independent verify");
                var after = SaveUtil.GetVariantSAV((byte[])output.Clone())!;
                var before = parsed.GetBoxSlotAtIndex(box, slot);
                var changed = after.GetBoxSlotAtIndex(box, slot);
                Check(changed.CurrentFriendship == 255 && changed.ChecksumValid && changed.PID == before.PID,
                      label + " friendship 255 on the same Pokémon, still in its slot");
                var differing = Enumerable.Range(0, before.Data.Length).Where(i => before.Data[i] != changed.Data[i]).ToArray();
                Check(differing.All(i => i == field || i is 6 or 7) && differing.Contains(field),
                      label + " only the game's friendship byte (+checksum) changed");
                int other = field == 0xCA ? 0xA2 : 0xCA;
                Check(changed.Data[0xCB] == before.Data[0xCB] && changed.Data[0xA3] == before.Data[0xA3]
                      && changed.Data[other] == before.Data[other],
                      label + " Amie affection and the other friendship untouched");
                Check(changed.Species == before.Species && changed.Form == before.Form && changed.Nickname == before.Nickname
                      && changed.EXP == before.EXP && changed.CurrentLevel == before.CurrentLevel
                      && changed.HeldItem == before.HeldItem && changed.Nature == before.Nature
                      && changed.Ability == before.Ability && changed.IV_SPE == before.IV_SPE
                      && changed.EV_SPA == before.EV_SPA && changed.Move1 == 221 && changed.Move4 == 394,
                      label + " species, level, item, nature, ability, IVs, EVs and moves preserved");
                Check(after.PartyCount == parsed.PartyCount
                      && Enumerable.Range(0, parsed.PartyCount).All(i =>
                          parsed.GetPartySlotAtIndex(i).Data.AsSpan().SequenceEqual(after.GetPartySlotAtIndex(i).Data))
                      && Enumerable.Range(0, parsed.BoxCount).All(b => Enumerable.Range(0, 30).All(s => (b, s) == (box, slot)
                          || parsed.GetBoxSlotAtIndex(b, s).Data.AsSpan().SequenceEqual(after.GetBoxSlotAtIndex(b, s).Data))),
                      label + " the party and every other box slot unchanged (nothing moved to the party)");
                int offset = parsed.GetBoxSlotOffset(box, slot);
                var outside = Enumerable.Range(0, source.Length).Where(i => source[i] != output[i]
                    && (i < offset || i >= offset + 232)
                    && !(sigStart >= 0 && i >= sigStart && i < sigStart + MemeCrypto.SaveFileSignatureLength)).ToArray();
                Check(outside.Length <= 2, label + " outside the slot only the block checksum changed (" + outside.Length + ")");
                Check(after is not SAV7 || NativeSignature.VerifySave(output), label + " signature valid");
                Reject(BoxRequest(output, box, slot), "FRIENDSHIP_ALREADY_MAX", label + " repeat on 255");
                // A forged output that also fills another slot of that box is refused.
                var forged = SaveUtil.GetVariantSAV((byte[])output.Clone())!;
                PutBox(forged, TrainingChecks.Specimen(forged), box, slot == 29 ? 27 : 2);
                var bad = request.DeepClone().AsObject();
                bad["output_base64"] = Convert.ToBase64String(Write(forged));
                Check(Execute(bad, true)["status"]!.GetValue<string>() == "rejected", label + " forged change to another slot refused");
                if (game == "Y" && box == 0) File.WriteAllBytes(Path.Combine(outputRoot, "Y-box-output.sav"), output);
            }
            Reject(BoxRequest(source, 0, 1), "UNSAFE_TARGET", game + " empty box slot");
            Reject(BoxRequest(source, 1, 5), "UNSAFE_TARGET", game + " boxed egg");
            Reject(BoxRequest(source, 0, 0, r => { r["intent"]!["mutation"]!["slot_index"] = 2; return r; }),
                   "UNSAFE_TARGET", game + " the chosen Pokémon is no longer in that slot (empty now)");
            Reject(BoxRequest(source, 0, 0, r => { r["intent"]!["mutation"]!["box_index"] = lastBox; r["intent"]!["mutation"]!["slot_index"] = 29; return r; }),
                   "STALE_MUTATION", game + " another Pokémon in that slot is never changed");
            Reject(BoxRequest(source, 0, 0, r => { r["intent"]!["mutation"]!["expected_friendship"] = 51; return r; }),
                   "STALE_MUTATION", game + " box friendship changed since shown");
            if (parsed.BoxCount < 32)
                Reject(BoxRequest(source, 0, 0, r => { r["intent"]!["mutation"]!["box_index"] = parsed.BoxCount; return r; }),
                       "UNSAFE_TARGET", game + " a box this game does not have");
            Reject(BoxRequest(source, 0, 0, r => { r["intent"]!["mutation"]!["box_index"] = 32; return r; }),
                   "INVALID_REQUEST", game + " box index out of range");
            Reject(BoxRequest(source, 0, 0, r => { r["intent"]!["mutation"]!["slot_index"] = 30; return r; }),
                   "INVALID_REQUEST", game + " box slot out of range");
            Reject(BoxRequest(source, 0, 0, r => { r["intent"]!["mutation"]!.AsObject().Remove("box_index"); return r; }),
                   "INVALID_REQUEST", game + " a box change without its box");
            Reject(Request(source, 0, r => { r["intent"]!["mutation"]!["box_index"] = 0; return r; }),
                   "INVALID_REQUEST", game + " a party change never names a box");
            Reject(BoxRequest(source, 0, 0, r => { r["intent"]!["mutation"]!["location"] = "pc"; return r; }),
                   "INVALID_REQUEST", game + " unknown location");
            report.Add(new { game, checks });
        }
        File.WriteAllText(Path.Combine(outputRoot, "friendship-checks.json"),
            JsonSerializer.Serialize(new { result = "PASS", checks, games = report }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"PASS friendship: {checks} checks across 8 games");
    }
}
