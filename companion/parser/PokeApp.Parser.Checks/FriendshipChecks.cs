using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;
using System.Text.Json.Nodes;

// «Felicidad máxima» on in-memory copies of the retained public contributor
// fixtures (never a player's save). A deliberately randomized party: a species
// with moves it cannot learn, a traded Pokémon held by another handler, one
// already at 255 and an egg. Proves the exact byte change and every refusal.
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
            report.Add(new { game, checks });
        }
        File.WriteAllText(Path.Combine(outputRoot, "friendship-checks.json"),
            JsonSerializer.Serialize(new { result = "PASS", checks, games = report }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"PASS friendship: {checks} checks across 8 games");
    }
}
