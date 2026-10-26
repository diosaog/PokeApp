using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;
using System.Text.Json.Nodes;

// Party-source robbery on derived copies of retained public fixtures only.
internal static class PartyTransferChecks
{
    // Same qualified origin boundary as the native remove path (24A contract).
    // Own OT and an identity (PID/EC) unique in the save; clones are never robbable.
    private static bool Own(PKM p, SaveFile s) => p.TID16 == s.TID16 && p.SID16 == s.SID16
        && p.OriginalTrainerName == s.OT && p.OriginalTrainerGender == s.Gender && p.Language == s.Language
        && s.BoxData.Concat(s.PartyData).Count(x => x.Species != 0 && (x.PID == p.PID || x.EncryptionConstant == p.EncryptionConstant)) == 1;

    public static void Run(string fixtureRoot, string outputRoot)
    {
        int checks = 0;
        void Check(bool ok, string label) { if (!ok) throw new Exception(label); checks++; }
        JsonNode Node(object o) => JsonSerializer.SerializeToNode(o, Inspection.Json)!;
        JsonNode Plan(JsonNode r) => Node(NativeTransfer.Plan(JsonSerializer.SerializeToUtf8Bytes(r)));
        JsonNode Apply(JsonNode r, bool verify = false) => Node(NativeWrite.Execute(JsonSerializer.SerializeToUtf8Bytes(r), verify));
        string Status(JsonNode n) => n["status"]!.GetValue<string>() == "rejected" ? n["error"]!.GetValue<string>() : n["status"]!.GetValue<string>();
        var games = new List<object>();
        foreach (var game in new[] { "X", "Y", "OR", "AS", "SN", "MN", "US", "UM" })
        {
            var donor = SaveUtil.GetVariantSAV(File.ReadAllBytes(Path.Combine(fixtureRoot, game, "expected")))!;
            // Derived copy with three party members, moved from Boxes 1-7 (eligible only).
            for (int i = 0; donor.PartyCount < 3 && i < 7 * 30; i++)
            {
                int bx = i / 30, s = i % 30;
                var pk = donor.GetBoxSlotAtIndex(bx, s);
                if (pk.Species == 0 || pk.IsEgg || !Own(pk, donor)) continue;
                pk.ResetPartyStats();
                donor.SetPartySlotAtIndex(pk, donor.PartyCount);
                donor.WriteBoxSlot(donor.BlankPKM, donor.Data.AsSpan(donor.GetBoxSlotOffset(bx, s), 232));
            }
            // A removal needs >= 2 members; fill with any non-egg Pokemon if needed.
            for (int i = 0; donor.PartyCount < 2 && i < 7 * 30; i++)
            {
                var pk = donor.GetBoxSlotAtIndex(i / 30, i % 30);
                if (pk.Species == 0 || pk.IsEgg) continue;
                pk.ResetPartyStats();
                donor.SetPartySlotAtIndex(pk, donor.PartyCount);
                donor.WriteBoxSlot(donor.BlankPKM, donor.Data.AsSpan(donor.GetBoxSlotOffset(i / 30, i % 30), 232));
            }
            Check(donor.PartyCount >= 2 && donor.PartyData.Any(x => Own(x, donor)), game + " party fixture with an eligible member");
            byte[] source = donor.Write();
            var receiverSave = donor.Clone(); receiverSave.OT = "Receiver"; receiverSave.TID16 ^= 0x1234; receiverSave.SID16 ^= 0x4321;
            for (int b = 0; b < receiverSave.BoxCount; b++) for (int s = 0; s < 30; s++)
                receiverSave.WriteBoxSlot(receiverSave.BlankPKM, receiverSave.Data.AsSpan(receiverSave.GetBoxSlotOffset(b, s), 232));
            receiverSave.PartyData = [];
            byte[] destination = receiverSave.Write();
            JsonObject Request(byte[] src, byte[] dst, int slot, PKM t) => new JsonObject {
                ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(src), ["destination_base64"] = Convert.ToBase64String(dst),
                ["pair_id"] = Guid.NewGuid().ToString(), ["location"] = "party", ["box_index"] = -1, ["slot_index"] = slot,
                ["target_pid"] = t.PID, ["target_ec"] = t.EncryptionConstant };
            var parsed = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
            int count = parsed.PartyCount, resign = 0;
            int foreign = 0;
            var eligible = Enumerable.Range(0, count).Where(i => Own(parsed.GetPartySlotAtIndex(i), parsed)).ToList();
            int chosen = eligible.Contains(1) ? 1 : eligible[0];
            var dir = Path.Combine(outputRoot, game); Directory.CreateDirectory(dir);
            File.WriteAllBytes(Path.Combine(dir, "source"), source); File.WriteAllBytes(Path.Combine(dir, "destination"), destination);
            for (int p = 0; p < count; p++)
            {
                var target = parsed.GetPartySlotAtIndex(p);
                var plan = Plan(Request(source, destination, p, target));
                bool own = Own(target, parsed);
                if (!own)
                {
                    // Qualified boundary: foreign OT or non-unique identity (clone) is refused.
                    Check(Status(plan) == "UNSAFE_TARGET", $"{game} ineligible party {p} refused");
                    foreign++;
                    continue;
                }
                if (Status(plan) == "CORRUPT_SAVE") { resign++; continue; } // Gen7 re-sign fails closed
                Check(Status(plan) == "planned", $"{game} plan party {p} {Status(plan)}");
                foreach (var side in new[] { "source", "destination" })
                {
                    var input = side == "source" ? source : destination;
                    var r = new JsonObject { ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(input), ["intent"] = plan["semantic_diff"]![side]!.DeepClone() };
                    var result = Apply(r);
                    Check(Status(result) == "prepared", $"{game} {side} {p}");
                    var output = Convert.FromBase64String(result["output_base64"]!.GetValue<string>());
                    var after = SaveUtil.GetVariantSAV((byte[])output.Clone())!;
                    if (side == "source")
                    {
                        Check(after.PartyCount == count - 1, game + " compacted count");
                        for (int i = 0; i < after.PartyCount; i++)
                            Check(after.GetPartySlotAtIndex(i).EncryptedPartyData.AsSpan().SequenceEqual(parsed.GetPartySlotAtIndex(i < p ? i : i + 1).EncryptedPartyData), game + " remaining members intact");
                        Check(after.BoxData.Concat(after.PartyData).All(x => x.Species == 0 || x.PID != target.PID && x.EncryptionConstant != target.EncryptionConstant), game + " removed, no clone");
                    }
                    else
                    {
                        var inserted = after.GetBoxSlotAtIndex(0, 0);
                        Check(inserted.EncryptedBoxData.AsSpan().SequenceEqual(target.EncryptedBoxData), game + " exact stored PKM");
                        Check(inserted.PID == target.PID && inserted.EncryptionConstant == target.EncryptionConstant && inserted.OriginalTrainerName == target.OriginalTrainerName
                            && inserted.TID16 == target.TID16 && inserted.EXP == target.EXP && inserted.IV_HP == target.IV_HP && inserted.IV_ATK == target.IV_ATK && inserted.IV_SPE == target.IV_SPE && inserted.Move1 == target.Move1, game + " identity/OT/IVs/EXP/moves kept");
                    }
                    r["output_base64"] = Convert.ToBase64String(output);
                    Check(Status(Apply(r, true)) == "verified", game + " independent verify " + side);
                    // Fixture for the PG journey: the middle eligible position when possible.
                    if (p == chosen) File.WriteAllBytes(Path.Combine(dir, side + "-result"), output);
                    var tampered = (byte[])output.Clone(); tampered[0x20] ^= 1; r["output_base64"] = Convert.ToBase64String(tampered);
                    Check(Status(Apply(r, true)) is "UNEXPECTED_DIFF" or "CORRUPT_SAVE", game + " tampered " + side);
                }
            }
            File.WriteAllText(Path.Combine(dir, "party-slot.txt"), (chosen + 1).ToString());
            Check(resign + foreign < count, game + " at least one own-OT position verified");
            int ownSlot = Enumerable.Range(0, count).First(i => Own(parsed.GetPartySlotAtIndex(i), parsed));
            var t0 = parsed.GetPartySlotAtIndex(ownSlot);
            var wrong = Request(source, destination, (ownSlot + 1) % count, t0);
            Check(Status(Plan(wrong)) == "UNSAFE_TARGET", game + " wrong Pokemon for slot");
            var single = parsed.Clone(); while (single.PartyCount > 1) single.DeletePartySlot(single.PartyCount - 1);
            var singleBytes = single.Write();
            Check(Status(Plan(Request(singleBytes, destination, 0, single.GetPartySlotAtIndex(0)))) is "LAST_PARTY_MEMBER" or "CORRUPT_SAVE", game + " last member refused");
            var full = receiverSave.Clone();
            for (int b = 0; b < 7; b++) for (int s = 0; s < 30; s++) { var f = t0.Clone(); f.PID += (uint)(1 + b * 30 + s); f.EncryptionConstant += (uint)(1 + b * 30 + s); f.RefreshChecksum(); full.WriteBoxSlot(f, full.Data.AsSpan(full.GetBoxSlotOffset(b, s), 232)); }
            Check(Status(Plan(Request(source, full.Write(), ownSlot, t0))) is "UNSAFE_TARGET" or "CORRUPT_SAVE", game + " destination full refused");
            var other = SaveUtil.GetVariantSAV(File.ReadAllBytes(Path.Combine(fixtureRoot, game == "X" ? "Y" : "X", "expected")))!;
            Check(Status(Plan(Request(source, other.Write(), ownSlot, t0))) == "WRONG_GAME", game + " cross-title refused");
            var stale = Request(source, destination, ownSlot, t0);
            var plan0 = Plan(stale);
            if (Status(plan0) == "planned")
            {
                var intent = plan0["semantic_diff"]!["source"]!.DeepClone(); intent["expected_sha256"] = new string('0', 64);
                Check(Status(Apply(new JsonObject { ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(source), ["intent"] = intent })) == "STALE_SOURCE", game + " stale source");
            }
            games.Add(new { game, party = count, positions_verified = count - resign - foreign, ineligible_refused = foreign, gen7_resign_rejections = resign });
        }
        Directory.CreateDirectory(outputRoot);
        File.WriteAllText(Path.Combine(outputRoot, "party-transfer-checks.json"), JsonSerializer.Serialize(new { status = "PASS", checks, games }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"PASS {checks} party-source transfer checks across 8 titles");
    }
}
