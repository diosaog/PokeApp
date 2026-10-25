using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;
using System.Text.Json.Nodes;

internal static class ReviveChecks
{
    private static int checks;
    private static void Check(bool ok, string label)
    {
        if (!ok) throw new Exception(label);
        checks++;
    }
    private static JsonElement Execute(JsonObject r, bool verify = false)
        => JsonSerializer.SerializeToElement(NativeWrite.Execute(JsonSerializer.SerializeToUtf8Bytes(r), verify), Inspection.Json);
    private static void Reject(JsonObject r, string label, bool verify = false)
        => Check(Execute(r, verify).GetProperty("status").GetString() == "rejected", label);
    private static JsonObject Request(byte[] bytes, SaveFile save, PKM mon) => new()
    {
        ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(bytes),
        ["intent"] = new JsonObject {
            ["game"] = save.Version.ToString(), ["expected_sha256"] = NativeWrite.Hash(bytes),
            ["trainer_key"] = NativeWrite.TrainerKey(save), ["mutation"] = new JsonObject {
                ["kind"] = "revive", ["location"] = "box", ["box_index"] = 7, ["slot_index"] = 0,
                ["target_pid"] = mon.PID, ["target_ec"] = mon.EncryptionConstant,
                ["destination_box_index"] = 0, ["destination_slot_index"] = 0
            }
        }
    };
    public static void Run(string manifestPath, string outputDirectory)
    {
        var output = Path.GetFullPath(outputDirectory);
        Directory.CreateDirectory(output);
        using var manifest = JsonDocument.Parse(File.ReadAllBytes(manifestPath));
        var root = Environment.ExpandEnvironmentVariables(manifest.RootElement.GetProperty("binary_root").GetString()!);
        var selected = new[] { "X-original/main", "Y-before-transfer/main", "OR/main", "AS-current/main", "SN/main", "MN/main", "US/main", "UM/main" };
        var evidence = new List<object>();
        foreach (var relative in selected)
        {
            var path = Path.Combine(root, relative);
            var original = File.ReadAllBytes(path);
            var metadata = manifest.RootElement.GetProperty("fixtures").EnumerateArray().Single(x => x.GetProperty("file").GetString() == relative);
            Check(NativeWrite.Hash(original) == metadata.GetProperty("sha256").GetString(), "manifest");
            var save = SaveUtil.GetVariantSAV((byte[])original.Clone())!;
            // Derived native-valid test state, not a claimed naturally dead Pokemon.
            // All setup is confined to copies of the contributed format fixtures.
            var mon = save.BoxData.Concat(save.PartyData).First(p => p.Species != 0 && !p.IsEgg).Clone();
            mon.TID16 = save.TID16; mon.SID16 = save.SID16;
            mon.OriginalTrainerName = save.OT; mon.OriginalTrainerGender = (byte)save.Gender;
            mon.Language = save.Language; mon.Version = save.Version;
            mon.PID = 0x1234ABCD; mon.EncryptionConstant = 0x5678ABCD;
            mon.MetDate = new DateOnly(2020, 1, 1); mon.MetLevel = 10; mon.MetLocation = 1;
            mon.EggLocation = 0; mon.EggMetDate = null; mon.RefreshChecksum();
            save.WriteBoxSlot(mon, save.Data.AsSpan(save.GetBoxSlotOffset(7, 0), 232));
            save.WriteBoxSlot(save.BlankPKM, save.Data.AsSpan(save.GetBoxSlotOffset(0, 0), 232));
            var source = save.Write();
            save = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
            var game = save.Version.ToString();
            var request = Request(source, save, mon);
            var result = Execute(request);
            Check(result.GetProperty("status").GetString() == "prepared", game + " prepare: " + result.GetProperty("error").GetString());
            var bytes = Convert.FromBase64String(result.GetProperty("output_base64").GetString()!);
            var after = SaveUtil.GetVariantSAV((byte[])bytes.Clone())!;
            Check(after.GetBoxSlotAtIndex(7, 0).Species == 0, game + " removed dead slot");
            Check(after.Data.AsSpan(after.GetBoxSlotOffset(0, 0), 232).SequenceEqual(save.Data.AsSpan(save.GetBoxSlotOffset(7, 0), 232)), game + " exact PKM bytes");
            Check(after.ChecksumsValid && after.GetBoxSlotAtIndex(0, 0).ChecksumValid, game + " integrity");
            Check(Execute(request).GetProperty("output_base64").GetString() == result.GetProperty("output_base64").GetString(), game + " deterministic");
            var verify = (JsonObject)request.DeepClone(); verify["output_base64"] = Convert.ToBase64String(bytes);
            Check(Execute(verify, true).GetProperty("status").GetString() == "verified", game + " verify");
            foreach (var (key, value) in new[] { ("slot_index", 1), ("box_index", 6), ("target_pid", 1), ("target_ec", 1), ("destination_slot_index", 1), ("destination_box_index", 7) })
            {
                var bad = (JsonObject)request.DeepClone(); bad["intent"]!["mutation"]![key] = value;
                Reject(bad, game + " bad " + key);
            }
            var stale = (JsonObject)request.DeepClone(); stale["intent"]!["expected_sha256"] = new string('0', 64); Reject(stale, "stale");
            stale = (JsonObject)request.DeepClone(); stale["intent"]!["trainer_key"] = new string('0', 64); Reject(stale, "trainer");
            var unchanged = (JsonObject)verify.DeepClone(); unchanged["output_base64"] = Convert.ToBase64String(source); Reject(unchanged, "unchanged", true);
            var tampered = (JsonObject)verify.DeepClone();
            after.Money = after.Money == 1 ? 2u : 1u; tampered["output_base64"] = Convert.ToBase64String(after.Write()); Reject(tampered, "valid extra money", true);
            after = SaveUtil.GetVariantSAV((byte[])bytes.Clone())!;
            var extra = after.GetBoxSlotAtIndex(0, 0); extra.IV_HP ^= 1; extra.RefreshChecksum();
            after.WriteBoxSlot(extra, after.Data.AsSpan(after.GetBoxSlotOffset(0, 0), 232));
            tampered["output_base64"] = Convert.ToBase64String(after.Write()); Reject(tampered, "valid extra IV", true);
            var badSave = save.Clone(); var egg = mon.Clone(); egg.IsEgg = true; egg.RefreshChecksum();
            badSave.WriteBoxSlot(egg, badSave.Data.AsSpan(badSave.GetBoxSlotOffset(7, 0), 232)); Reject(Request(badSave.Write(), badSave, egg), "egg");
            badSave = save.Clone(); badSave.WriteBoxSlot(mon, badSave.Data.AsSpan(badSave.GetBoxSlotOffset(0, 1), 232)); Reject(Request(badSave.Write(), badSave, mon), "clone identity");
            badSave = save.Clone();
            for (int b = 0; b < 7; b++) for (int s = 0; s < 30; s++)
            {
                var fill = mon.Clone(); fill.PID += (uint)(1 + b * 30 + s); fill.EncryptionConstant += (uint)(1 + b * 30 + s); fill.RefreshChecksum();
                badSave.WriteBoxSlot(fill, badSave.Data.AsSpan(badSave.GetBoxSlotOffset(b, s), 232));
            }
            Reject(Request(badSave.Write(), badSave, mon), "full boxes");
            var dir = Path.Combine(output, game); Directory.CreateDirectory(dir);
            File.WriteAllBytes(Path.Combine(dir, "source"), source);
            File.WriteAllBytes(Path.Combine(dir, "expected"), bytes);
            File.WriteAllText(Path.Combine(dir, "intent.json"), request["intent"]!.ToJsonString());
            // Existing reader sees the exact same fields, only slot ownership moves.
            var left = JsonSerializer.SerializeToNode(Inspection.Inspect(source), Inspection.Json)!;
            var right = JsonSerializer.SerializeToNode(Inspection.Inspect(bytes), Inspection.Json)!;
            Check(left["error"] is null && right["error"] is null, game + " parser read");
            var boxes = left["observation"]!["boxes"]!.AsArray(); var moved = boxes[7]!["slots"]![0]!.DeepClone();
            boxes[7]!["slots"]![0] = null; boxes[0]!["slots"]![0] = moved;
            Check(JsonNode.DeepEquals(left, right), game + " complete parser equality except move");
            Check(NativeWrite.Hash(File.ReadAllBytes(path)) == NativeWrite.Hash(original), "original unchanged");
            evidence.Add(new { game, original_sha256 = NativeWrite.Hash(original), source_sha256 = NativeWrite.Hash(source), result_sha256 = NativeWrite.Hash(bytes), status = "PASS", fixture = "authentic format fixture with synthetic own dead target; NOT gameplay certification" });
            Console.WriteLine("PASS REVIVE " + game);
        }
        File.WriteAllText(Path.Combine(output, "native-revive.json"), JsonSerializer.Serialize(new { status = "PASS", checks, games = evidence }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"PASS {checks} revive checks");
    }
}
