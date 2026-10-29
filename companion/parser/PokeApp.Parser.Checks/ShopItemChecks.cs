using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;
using System.Text.Json.Nodes;

// 072: one paid Shop object into the bag, on derived copies of retained public
// fixtures only. Which games hold each object must equal the server contract
// (app/domain/shop_item_uses.py: Bottle Caps and the Ice Stone only in Gen 7).
internal static class ShopItemChecks
{
    private static readonly HashSet<string> Gen7Only = ["bottle_cap", "gold_bottle_cap", "ice_stone"];

    public static void Run(string fixtureRoot, string outputRoot)
    {
        int checks = 0, resignRejected = 0;
        void Check(bool ok, string label) { if (!ok) throw new Exception(label); checks++; }
        JsonNode Node(object value) => JsonSerializer.SerializeToNode(value, Inspection.Json)!;
        JsonNode Inventory(byte[] save, IEnumerable<string> items) => Node(NativeItems.Inventory(JsonSerializer.SerializeToUtf8Bytes(
            new JsonObject
            {
                ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(save),
                ["items"] = new JsonArray(items.Select(i => (JsonNode)JsonValue.Create(i)!).ToArray()),
            })));
        JsonObject Mutation(string kind, string item, int quantity, int expected, string purchase, string attempt) => kind == "deliver_item"
            ? new JsonObject { ["kind"] = kind, ["item"] = item, ["quantity"] = quantity, ["expected_count"] = expected, ["purchase_id"] = purchase, ["attempt"] = attempt }
            : new JsonObject { ["kind"] = kind, ["item"] = item, ["quantity"] = quantity, ["expected_count"] = expected };
        JsonObject Request(byte[] save, string game, JsonObject mutation)
        {
            var parsed = SaveUtil.GetVariantSAV((byte[])save.Clone())!;
            return new JsonObject
            {
                ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(save),
                ["intent"] = new JsonObject
                {
                    ["game"] = game, ["expected_sha256"] = NativeWrite.Hash(save),
                    ["trainer_key"] = NativeWrite.TrainerKey(parsed), ["mutation"] = mutation,
                },
            };
        }
        JsonNode Apply(JsonObject r, bool verify = false) => Node(NativeWrite.Execute(JsonSerializer.SerializeToUtf8Bytes(r), verify));
        string Error(JsonNode n) => n["status"]!.GetValue<string>() == "rejected" ? n["error"]!.GetValue<string>() : "OK";
        const string Purchase = "c0000000-0000-4000-8000-000000000001", Attempt = "d0000000-0000-4000-8000-000000000002";

        var names = NativeItems.ShopItems.Keys.ToArray();
        var games = new List<object>();
        foreach (var game in new[] { "X", "Y", "OR", "AS", "SN", "MN", "US", "UM" })
        {
            bool gen7 = game is "SN" or "MN" or "US" or "UM";
            var source = File.ReadAllBytes(Path.Combine(fixtureRoot, game, "expected"));
            var counts = new Dictionary<string, (int count, int max, int addable)>();
            foreach (var chunk in names.Chunk(8))
            {
                var read = Inventory(source, chunk);
                Check(read["status"]!.GetValue<string>() == "inspected", game + " shop inventory read");
                foreach (var name in chunk)
                {
                    var info = read["semantic_diff"]![name]!;
                    counts[name] = (info["count"]!.GetValue<int>(), info["max"]!.GetValue<int>(), info["addable"]!.GetValue<int>());
                }
            }
            foreach (var name in names)
            {
                bool holdable = counts[name].max > 0;
                Check(holdable == (gen7 || !Gen7Only.Contains(name)), game + " " + name + " compatibility");
            }
            // The default read (no `items`) still answers the quick items only.
            var quick = Node(NativeItems.Inventory(JsonSerializer.SerializeToUtf8Bytes(
                new JsonObject { ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(source) })));
            Check(quick["semantic_diff"]!.AsObject().Select(p => p.Key).OrderBy(k => k).SequenceEqual(["heart_scale", "rare_candy"]), game + " quick read unchanged");
            Check(Error(Inventory(source, ["master_ball"])) == "INVALID_REQUEST", game + " unknown inventory name");

            // One object per family: berry, held item, gem, evolution, fossil (+ Bottle Cap in Gen 7).
            var delivered = new List<string>();
            foreach (var name in new[] { "sitrus_berry", "leftovers", "fire_gem", "dusk_stone", "helix_fossil", "bottle_cap" })
            {
                var (count, max, addable) = counts[name];
                if (max == 0)
                {
                    Check(Error(Apply(Request(source, game, Mutation("deliver_item", name, 1, 0, Purchase, Attempt)))) == "UNSUPPORTED_FORMAT",
                        game + " " + name + " refused where the bag cannot hold it");
                    continue;
                }
                if (addable == 0) continue;
                var prepared = Apply(Request(source, game, Mutation("deliver_item", name, 1, count, Purchase, Attempt)));
                if (Error(prepared) == "CORRUPT_SAVE")
                {
                    // Gen7 re-signing is content-dependent: fails closed, no output.
                    Check(prepared["output_base64"] is null, game + " resign rejection has no output");
                    resignRejected++;
                    continue;
                }
                Check(Error(prepared) == "OK", game + " " + name + " prepare " + Error(prepared));
                var diff = prepared["semantic_diff"]!;
                Check(diff["kind"]!.GetValue<string>() == "deliver_item" && diff["purchase_id"]!.GetValue<string>() == Purchase
                    && diff["attempt"]!.GetValue<string>() == Attempt && diff["quantity"]!.GetValue<int>() == 1, game + " echoed delivery");
                var output = Convert.FromBase64String(prepared["output_base64"]!.GetValue<string>());
                var verify = Request(source, game, Mutation("deliver_item", name, 1, count, Purchase, Attempt));
                verify["output_base64"] = Convert.ToBase64String(output);
                Check(Error(Apply(verify, true)) == "OK", game + " " + name + " verify");
                var others = names.Where(n => n != name && counts[n].max > 0).Take(7).ToArray();
                var after = Inventory(output, others.Append(name))["semantic_diff"]!;
                Check(after[name]!["count"]!.GetValue<int>() == count + 1, game + " " + name + " readback +1");
                foreach (var other in others)
                    Check(after[other]!["count"]!.GetValue<int>() == counts[other].count, game + " " + other + " untouched");
                Check(Error(Apply(Request(output, game, Mutation("deliver_item", name, 1, count, Purchase, Attempt)))) == "STALE_MUTATION",
                    game + " replay on the delivered save");
                var tampered = (byte[])output.Clone();
                tampered[0x10] ^= 1;
                verify["output_base64"] = Convert.ToBase64String(tampered);
                Check(Error(Apply(verify, true)) == "UNEXPECTED_DIFF", game + " tampered output");
                delivered.Add(name);
            }
            Check(delivered.Count >= 3, game + " delivered objects " + delivered.Count);

            // Refusals: one object per purchase, Shop list only, never the free items, well-formed ids.
            var berry = counts["sitrus_berry"].count;
            Check(Error(Apply(Request(source, game, Mutation("deliver_item", "sitrus_berry", 2, berry, Purchase, Attempt)))) == "INVENTORY_LIMIT", game + " two objects");
            Check(Error(Apply(Request(source, game, Mutation("deliver_item", "master_ball", 1, 0, Purchase, Attempt)))) == "UNSAFE_TARGET", game + " unlisted object");
            Check(Error(Apply(Request(source, game, Mutation("deliver_item", "rare_candy", 1, 0, Purchase, Attempt)))) == "UNSAFE_TARGET", game + " free item is not a Shop delivery");
            Check(Error(Apply(Request(source, game, Mutation("add_item", "sitrus_berry", 1, berry, Purchase, Attempt)))) == "UNSAFE_TARGET", game + " Shop object is not a quick item");
            Check(Error(Apply(Request(source, game, Mutation("deliver_item", "sitrus_berry", 1, berry, "not-a-uuid", Attempt)))) == "INVALID_REQUEST", game + " purchase id");
            Check(Error(Apply(Request(source, game, Mutation("deliver_item", "sitrus_berry", 1, berry + 1, Purchase, Attempt)))) == "STALE_MUTATION", game + " stale count");
            var missing = Mutation("deliver_item", "sitrus_berry", 1, berry, Purchase, Attempt);
            missing.Remove("attempt");
            Check(Error(Apply(Request(source, game, missing))) == "INVALID_REQUEST", game + " attempt required");
            games.Add(new { game, delivered });
        }
        Directory.CreateDirectory(outputRoot);
        File.WriteAllText(Path.Combine(outputRoot, "shop-item-checks.json"),
            JsonSerializer.Serialize(new { status = "PASS", checks, objects = names.Length, gen7_resign_rejections_fail_closed = resignRejected, games }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"PASS {checks} shop-object checks across 8 titles ({names.Length} objects); {resignRejected} Gen7 re-sign rejections failed closed");
    }
}
