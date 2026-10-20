using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;
using System.Text.Json.Nodes;

// Real contributor fixtures are read only. All changed bytes stay in the
// explicitly supplied private test output. No owner paths or mutations.
internal static class WriteChecks
{
    private static int checks;
    private static void Check(bool condition, string label)
    {
        if (!condition) throw new Exception(label);
        checks++;
        Console.WriteLine("PASS WRITE " + label);
    }

    private static JsonElement Execute(JsonObject request, bool verify = false)
        => JsonSerializer.SerializeToElement(NativeWrite.Execute(
            JsonSerializer.SerializeToUtf8Bytes(request), verify), Inspection.Json);
    private static JsonObject Clone(JsonObject node) => (JsonObject)node.DeepClone();
    private static void Rejected(JsonObject request, string label, bool verify = false)
    {
        var response = Execute(request, verify);
        Check(response.GetProperty("status").GetString() == "rejected"
            && response.GetProperty("error").ValueKind == JsonValueKind.String
            && response.GetProperty("output_base64").ValueKind == JsonValueKind.Null, label);
    }
    private static int Mark(PKM pk) => pk is PK6 p ? p.MarkingValue : ((PK7)pk).MarkingValue;
    private static int NextMark(PKM pk)
    {
        int old = Mark(pk);
        return pk is PK6 ? old ^ 1 : (old & ~3) | (((old & 3) + 1) % 3);
    }

    public static void Run(string manifestPath, string outputDirectory)
    {
        var output = Path.GetFullPath(outputDirectory);
        Directory.CreateDirectory(output);
        using var manifest = JsonDocument.Parse(File.ReadAllBytes(manifestPath));
        var sourceRoot = Environment.ExpandEnvironmentVariables(manifest.RootElement.GetProperty("binary_root").GetString()!);
        var selected = new Dictionary<string, string>
        {
            ["X"] = "X-original/main", ["Y"] = "Y-before-transfer/main",
            ["OR"] = "OR/main", ["AS"] = "AS-current/main",
            ["SN"] = "SN/main", ["MN"] = "MN/main", ["US"] = "US/main", ["UM"] = "UM/main",
        };
        var evidence = new List<object>();
        var intents = new List<object>();
        foreach (var (game, relativePath) in selected)
        {
            var metadata = manifest.RootElement.GetProperty("fixtures").EnumerateArray()
                .Single(f => f.GetProperty("file").GetString() == relativePath);
            var sourcePath = Path.GetFullPath(Path.Combine(sourceRoot, relativePath));
            var bytes = File.ReadAllBytes(sourcePath);
            var sourceHash = NativeWrite.Hash(bytes);
            Check(sourceHash == metadata.GetProperty("sha256").GetString(), game + " real fixture matches retained manifest");
            var originalReader = JsonSerializer.Serialize(Inspection.Inspect(bytes), Inspection.Json);
            var source = SaveUtil.GetVariantSAV((byte[])bytes.Clone())!;
            (string location, int? box, int slot, PKM pokemon) = SelectTarget(source);
            var request = Request(bytes, source, location, box, slot, pokemon);
            var result = Execute(request);
            Check(result.GetProperty("status").GetString() == "prepared",
                game + " prepared " + result.GetProperty("error").GetString());
            var changedBytes = Convert.FromBase64String(result.GetProperty("output_base64").GetString()!);
            var changed = SaveUtil.GetVariantSAV((byte[])changedBytes.Clone())!;
            var changedPokemon = location == "box" ? changed.GetBoxSlotAtIndex(box!.Value, slot) : changed.GetPartySlotAtIndex(slot);
            Check(Mark(changedPokemon) == NextMark(pokemon) && Mark(changedPokemon) != Mark(pokemon), game + " actual native marking changed");
            Check(changed.ChecksumsValid && changedPokemon.ChecksumValid, game + " save/PKM checksums valid");
            Check(changedBytes.Length == bytes.Length && NativeWrite.Hash(changedBytes) != sourceHash, game + " same native size, distinct bytes");
            Check(originalReader == JsonSerializer.Serialize(Inspection.Inspect(changedBytes), Inspection.Json),
                game + " independent full read unchanged (including private/progression/party/PC)");
            var repeated = Execute(request);
            Check(repeated.GetProperty("output_base64").GetString() == result.GetProperty("output_base64").GetString(),
                game + " deterministic duplicate preparation");
            var verify = Clone(request);
            verify["output_base64"] = Convert.ToBase64String(changedBytes);
            Check(Execute(verify, true).GetProperty("status").GetString() == "verified", game + " independent byte verification");

            var altered = Clone(request);
            altered["intent"]!["trainer_key"] = new string('0', 64);
            Rejected(altered, game + " wrong trainer denied");
            altered = Clone(request); altered["intent"]!["expected_sha256"] = new string('0', 64);
            Rejected(altered, game + " stale original denied");
            altered = Clone(request); altered["intent"]!["game"] = game == "X" ? "Y" : "X";
            Rejected(altered, game + " wrong game denied");
            altered = Clone(request); altered["intent"]!["mutation"]!["new_value"] = Mark(pokemon);
            Rejected(altered, game + " no-op denied");
            altered = Clone(request); altered["intent"]!["mutation"]!["expected_original"] = Mark(pokemon) + 1;
            Rejected(altered, game + " stale mutation denied");
            altered = Clone(request); altered["intent"]!["mutation"]!["slot_index"] = 9999;
            Rejected(altered, game + " invalid target denied");
            altered = Clone(request); altered["intent"]!["mutation"]!["new_value"] = source.Generation == 6 ? 64 : 3;
            Rejected(altered, game + " reserved/out-of-range marking denied");
            altered = Clone(request); altered["path"] = "never-open.sav";
            Rejected(altered, game + " file path forbidden");
            altered = Clone(request); altered["intent"]!["mutation"]!["kind"] = "grant_item";
            Rejected(altered, game + " business operation forbidden");
            altered = Clone(request); altered["source_base64"] = Convert.ToBase64String(bytes[..^1]);
            Rejected(altered, game + " truncated source denied");
            var corrupt = (byte[])bytes.Clone(); corrupt[0x100] ^= 1;
            altered = Clone(request); altered["source_base64"] = Convert.ToBase64String(corrupt);
            Rejected(altered, game + " corrupt source denied");
            altered = Clone(verify); altered["output_base64"] = Convert.ToBase64String(bytes);
            Rejected(altered, game + " unchanged output denied", true);
            corrupt = (byte[])changedBytes.Clone(); corrupt[0x100] ^= 1;
            altered = Clone(verify); altered["output_base64"] = Convert.ToBase64String(corrupt);
            Rejected(altered, game + " corrupt persisted bytes denied", true);

            // Independently serialize valid native changes outside the approved
            // plan: checksums/signatures alone must not authorize extra effects.
            changed.Money = changed.Money == 1 ? 2u : 1u;
            altered = Clone(verify); altered["output_base64"] = Convert.ToBase64String(changed.Write());
            Rejected(altered, game + " valid-checksum unrelated money mutation denied", true);
            changed = SaveUtil.GetVariantSAV((byte[])changedBytes.Clone())!;
            changedPokemon = location == "box" ? changed.GetBoxSlotAtIndex(box!.Value, slot) : changed.GetPartySlotAtIndex(slot);
            changedPokemon.IV_HP = changedPokemon.IV_HP == 31 ? 30 : 31;
            changedPokemon.RefreshChecksum();
            if (location == "box")
                changed.WriteBoxSlot(changedPokemon, changed.Data.AsSpan(changed.GetBoxSlotOffset(box!.Value, slot), 232));
            else
                changed.WritePartySlot(changedPokemon, changed.Data.AsSpan(changed.GetPartyOffset(slot), 260));
            altered = Clone(verify); altered["output_base64"] = Convert.ToBase64String(changed.Write());
            Rejected(altered, game + " valid-checksum extra private-PKM mutation denied", true);

            // Party serialization must preserve battle stats and all trailing
            // party bytes too, including Gen6 where the main proof used a box.
            var partySlot = Enumerable.Range(0, source.PartyCount).FirstOrDefault(
                i => source.GetPartySlotAtIndex(i) is { Species: not 0, IsEgg: false }, -1);
            if (partySlot >= 0)
            {
                var partyRequest = Request(bytes, source, "party", null, partySlot, source.GetPartySlotAtIndex(partySlot));
                var partyResult = Execute(partyRequest);
                Check(partyResult.GetProperty("status").GetString() == "prepared", game + " party native byte preservation");
                partyRequest["output_base64"] = partyResult.GetProperty("output_base64").GetString();
                Check(Execute(partyRequest, true).GetProperty("status").GetString() == "verified", game + " party independently verified");
            }

            // Persist the disposable result and re-read it through the protocol.
            var gameOutput = Path.Combine(output, game);
            Directory.CreateDirectory(gameOutput);
            var disposable = Path.Combine(gameOutput, "prepared");
            File.WriteAllBytes(disposable, changedBytes);
            altered = Clone(verify); altered["output_base64"] = Convert.ToBase64String(File.ReadAllBytes(disposable));
            Check(Execute(altered, true).GetProperty("status").GetString() == "verified", game + " persisted disposable reparse");
            Check(sourceHash == NativeWrite.Hash(File.ReadAllBytes(sourcePath)), game + " contributor original unchanged");
            Check(originalReader == JsonSerializer.Serialize(Inspection.Inspect(bytes), Inspection.Json), game + " source array unchanged");
            // Store protocol input privately for Python/file transaction/package
            // tests. Contains public contributor bytes, never an owner save.
            File.WriteAllText(Path.Combine(gameOutput, "request.json"), request.ToJsonString());
            intents.Add(new { game, source = relativePath, source_sha256 = sourceHash,
                output_sha256 = NativeWrite.Hash(changedBytes), intent = request["intent"]!.DeepClone() });
            evidence.Add(new
            {
                game, source = relativePath, source_sha256 = sourceHash,
                output_sha256 = NativeWrite.Hash(changedBytes), bytes = bytes.Length, location, box, slot,
                native_nontrivial_write = "PASS", original_unchanged = true,
                checksum_signature = "PASS", whole_native_diff = "PASS",
                source_limitation = metadata.GetProperty("provenance").GetString(),
            });
        }
        // Malformed/duplicate JSON is rejected rather than silently selecting
        // one of two different authority values.
        var duplicate = "{\"schema_version\":1,\"schema_version\":1,\"source_base64\":\"\",\"intent\":{}}";
        var duplicateResult = JsonSerializer.SerializeToElement(NativeWrite.Execute(System.Text.Encoding.UTF8.GetBytes(duplicate), false), Inspection.Json);
        Check(duplicateResult.GetProperty("error").GetString() == "INVALID_REQUEST", "duplicate JSON keys rejected");
        var summary = new
        {
            schema_version = 1, writer_version = NativeWrite.WriterVersion, checks, games = evidence,
            boundary = "Native bytes-only protocol. Filesystem backup/atomicity/recovery is certified separately. Originals read only; test output is private.",
        };
        File.WriteAllText(Path.Combine(output, "native-write-evidence.json"), JsonSerializer.Serialize(summary, new JsonSerializerOptions { WriteIndented = true }));
        File.WriteAllText(Path.Combine(output, "native-write-intents.json"), JsonSerializer.Serialize(intents, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"RESULT OK; {checks} native write checks; eight real contributor fixture games");
    }

    private static (string, int?, int, PKM) SelectTarget(SaveFile save)
    {
        for (int b = 0; b < save.BoxCount; b++)
            for (int s = 0; s < save.BoxSlotCount; s++)
            {
                var p = save.GetBoxSlotAtIndex(b, s);
                if (p.Species != 0 && !p.IsEgg && !save.IsBoxSlotOverwriteProtected(b, s))
                    return ("box", b, s, p);
            }
        for (int s = 0; s < save.PartyCount; s++)
        {
            var p = save.GetPartySlotAtIndex(s);
            if (p.Species != 0 && !p.IsEgg) return ("party", null, s, p);
        }
        throw new Exception("No eligible real fixture Pokemon.");
    }

    private static JsonObject Request(byte[] sourceBytes, SaveFile source, string location, int? box, int slot, PKM pokemon)
        => new()
        {
            ["schema_version"] = 1,
            ["source_base64"] = Convert.ToBase64String(sourceBytes),
            ["intent"] = new JsonObject
            {
                ["game"] = source.Version.ToString(), ["expected_sha256"] = NativeWrite.Hash(sourceBytes),
                ["trainer_key"] = NativeWrite.TrainerKey(source),
                ["mutation"] = new JsonObject
                {
                    ["kind"] = "test_marking", ["location"] = location, ["box_index"] = box,
                    ["slot_index"] = slot, ["expected_original"] = Mark(pokemon), ["new_value"] = NextMark(pokemon),
                },
            },
        };
}
