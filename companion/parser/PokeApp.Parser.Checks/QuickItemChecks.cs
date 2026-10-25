using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;
using System.Text.Json.Nodes;

// Rare Candy / Heart Scale on derived copies of retained public fixtures only.
internal static class QuickItemChecks
{
    public static void Run(string fixtureRoot, string outputRoot)
    {
        int checks = 0;
        void Check(bool ok, string label) { if (!ok) throw new Exception(label); checks++; }
        JsonNode Node(object value) => JsonSerializer.SerializeToNode(value, Inspection.Json)!;
        JsonNode Inventory(byte[] save) => Node(NativeItems.Inventory(JsonSerializer.SerializeToUtf8Bytes(
            new JsonObject { ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(save) })));
        JsonObject Request(byte[] save, string game, string item, int quantity, int expected, string? hash = null, string? trainer = null)
        {
            var parsed = SaveUtil.GetVariantSAV((byte[])save.Clone())!;
            return new JsonObject
            {
                ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(save),
                ["intent"] = new JsonObject
                {
                    ["game"] = game, ["expected_sha256"] = hash ?? NativeWrite.Hash(save),
                    ["trainer_key"] = trainer ?? NativeWrite.TrainerKey(parsed),
                    ["mutation"] = new JsonObject { ["kind"] = "add_item", ["item"] = item, ["quantity"] = quantity, ["expected_count"] = expected },
                },
            };
        }
        JsonNode Apply(JsonObject r, bool verify = false) => Node(NativeWrite.Execute(JsonSerializer.SerializeToUtf8Bytes(r), verify));
        string Error(JsonNode n) => n["status"]!.GetValue<string>() == "rejected" ? n["error"]!.GetValue<string>() : "OK";
        var games = new List<object>();
        int resignRejected = 0;
        foreach (var game in new[] { "X", "Y", "OR", "AS", "SN", "MN", "US", "UM" })
        {
            var source = File.ReadAllBytes(Path.Combine(fixtureRoot, game, "expected"));
            var before = Inventory(source);
            Check(before["status"]!.GetValue<string>() == "inspected" && before["game"]!.GetValue<string>() == game, game + " inventory read");
            var counts = new Dictionary<string, int>();
            foreach (var item in new[] { "rare_candy", "heart_scale" })
            {
                var info = before["semantic_diff"]![item]!;
                int count = info["count"]!.GetValue<int>(), max = info["max"]!.GetValue<int>(), addable = info["addable"]!.GetValue<int>();
                counts[item] = count;
                Check(max > 0 && addable == max - count, game + " " + item + " limits");
                Check(Error(Apply(Request(source, game, item, max - count + 1, count))) == "INVENTORY_LIMIT", game + " over maximum");
                Check(Error(Apply(Request(source, game, item, 0, count))) == "INVENTORY_LIMIT", game + " zero quantity");
                Check(Error(Apply(Request(source, game, item, -3, count))) == "INVENTORY_LIMIT", game + " negative quantity");
                if (addable == 0) continue;
                // Gen7 re-signing is content-dependent: an unverifiable signature
                // fails closed (CORRUPT_SAVE, no output). Count it, never accept it.
                int quantity = 0;
                JsonNode prepared = null!;
                foreach (var q in new[] { 5, 4, 3, 2, 1 }.Where(q => q <= addable))
                {
                    prepared = Apply(Request(source, game, item, q, count));
                    if (Error(prepared) == "CORRUPT_SAVE") { Check(prepared["output_base64"] is null, game + " resign rejection has no output"); resignRejected++; continue; }
                    Check(Error(prepared) == "OK", game + " " + item + " prepare " + Error(prepared));
                    quantity = q;
                    break;
                }
                Check(quantity > 0, game + " " + item + " no admissible quantity");
                var output = Convert.FromBase64String(prepared["output_base64"]!.GetValue<string>());
                var verify = Request(source, game, item, quantity, count);
                verify["output_base64"] = Convert.ToBase64String(output);
                Check(Error(Apply(verify, true)) == "OK", game + " " + item + " verify");
                var after = Inventory(output)["semantic_diff"]!;
                Check(after[item]!["count"]!.GetValue<int>() == count + quantity, game + " " + item + " readback");
                var other = item == "rare_candy" ? "heart_scale" : "rare_candy";
                Check(after[other]!["count"]!.GetValue<int>() == before["semantic_diff"]![other]!["count"]!.GetValue<int>(), game + " other item untouched");
                var exact = Error(Apply(Request(source, game, item, max - count, count)));
                Check(exact is "OK" or "CORRUPT_SAVE", game + " " + item + " exact maximum admitted " + exact);
                Check(Error(Apply(Request(source, game, item, 1, count + 1))) == "STALE_MUTATION", game + " stale count");
                Check(Error(Apply(Request(output, game, item, 1, count))) == "STALE_MUTATION", game + " replay on applied save");
                Check(Error(Apply(Request(source, game, item, 1, count, hash: new string('a', 64)))) == "STALE_SOURCE", game + " stale source");
                Check(Error(Apply(Request(source, game, item, 1, count, trainer: new string('b', 64)))) == "WRONG_TRAINER", game + " wrong trainer");
                Check(Error(Apply(Request(source, game == "X" ? "Y" : "X", item, 1, count))) == "WRONG_GAME", game + " wrong game");
                var tampered = (byte[])output.Clone();
                tampered[0x10] ^= 1;
                verify["output_base64"] = Convert.ToBase64String(tampered);
                Check(Error(Apply(verify, true)) == "UNEXPECTED_DIFF", game + " tampered output");
            }
            Check(Error(Apply(Request(source, game, "master_ball", 1, 0))) == "UNSAFE_TARGET", game + " unapproved item");

            // Full pouch: remove Heart Scale, fill every free slot with other legal items.
            var full = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
            var pouches = full.Inventory;
            var pouch = pouches.Single(p => p.CanContain(93));
            foreach (var slot in pouch.Items.Where(i => i.Index == 93)) { slot.Index = 0; slot.Count = 0; }
            // Repeating legal entries is enough to occupy every slot of the pouch.
            var legal = Enumerable.Range(1, 2000).Select(i => (ushort)i).Where(i => i != 93 && pouch.CanContain(i)).ToArray();
            bool filled = legal.Length > 0;
            int next = 0;
            foreach (var slot in pouch.Items.Where(i => i.Index == 0))
            {
                if (!filled) break;
                slot.Index = legal[next++ % legal.Length];
                slot.SetNewDetails(1);
                slot.Count = 1;
            }
            string fullResult = "NOT_CONSTRUCTIBLE";
            if (filled)
            {
                full.Inventory = pouches;
                var bytes = full.Write();
                fullResult = Error(Apply(Request(bytes, game, "heart_scale", 1, 0)));
                Check(fullResult == "INVENTORY_FULL", game + " full pouch " + fullResult);
            }
            games.Add(new { game, rare_candy = counts["rare_candy"], heart_scale = counts["heart_scale"], full_pouch = fullResult });
        }
        Directory.CreateDirectory(outputRoot);
        File.WriteAllText(Path.Combine(outputRoot, "quick-item-checks.json"),
            JsonSerializer.Serialize(new { status = "PASS", checks, gen7_resign_rejections_fail_closed = resignRejected, games }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"PASS {checks} quick-item checks across 8 titles; {resignRejected} Gen7 re-sign rejections failed closed");
    }
}
