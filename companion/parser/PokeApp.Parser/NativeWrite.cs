using PKHeX.Core;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace PokeApp.Parser;

// Local native byte transformation only. This is not filesystem or competitive
// authority. Native transformations never grant permission to publish a file.
public static class NativeWrite
{
    public const string WriterVersion = "pokeapp-writer/1;pkhex/24.11.11";
    public const int MaxRequestBytes = 2 * 1024 * 1024;
    private const int StoredSize = 232;
    private const int PartySize = 260;

    private sealed record Mutation(string Kind, string Location, int? BoxIndex, int SlotIndex,
        int ExpectedOriginal, int NewValue);
    private sealed record Intent(string Game, string ExpectedSha256, string TrainerKey, Mutation Mutation);
    internal sealed class Rejection(string code) : Exception
    {
        public string Code { get; } = code;
    }

    public static string Hash(ReadOnlySpan<byte> bytes)
        => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    // Neutral and explicit: game + NUL + exact OT + NUL + decimal TID + NUL +
    // decimal SID + NUL + decimal gender + NUL + decimal language. No paths,
    // host identifiers, inferred UUIDs or mutable party data enter this key.
    public static string TrainerKey(SaveFile save) => Hash(Encoding.UTF8.GetBytes(string.Join('\0',
        save.Version.ToString(), save.OT,
        save.TID16.ToString(CultureInfo.InvariantCulture), save.SID16.ToString(CultureInfo.InvariantCulture),
        save.Gender.ToString(CultureInfo.InvariantCulture), save.Language.ToString(CultureInfo.InvariantCulture))));

    public static object Execute(ReadOnlySpan<byte> request, bool verify)
    {
        try
        {
            if (request.Length is 0 or > MaxRequestBytes) throw new Rejection("INVALID_REQUEST");
            using var document = JsonDocument.Parse(request.ToArray(), new JsonDocumentOptions { MaxDepth = 8 });
            var root = document.RootElement;
            Exact(root, verify ? ["schema_version", "source_base64", "output_base64", "intent"]
                               : ["schema_version", "source_base64", "intent"]);
            if (Integer(root, "schema_version") != 1) throw new Rejection("INVALID_REQUEST");
            if (Text(root.GetProperty("intent").GetProperty("mutation"), "kind") == "revive")
                return NativeRevive.Execute(root, verify);
            if (Text(root.GetProperty("intent").GetProperty("mutation"), "kind") is "transfer_remove" or "transfer_insert")
                return NativeTransfer.Execute(root, verify);
            var intent = ParseIntent(root.GetProperty("intent"));
            var original = Bytes(root, "source_base64");
            var source = Validate(original);
            if (!string.Equals(Hash(original), intent.ExpectedSha256, StringComparison.Ordinal))
                throw new Rejection("STALE_SOURCE");
            if (source.Version.ToString() != intent.Game) throw new Rejection("WRONG_GAME");
            if (TrainerKey(source) != intent.TrainerKey) throw new Rejection("WRONG_TRAINER");
            var before = Target(source, intent.Mutation);
            if (Mark(before) != intent.Mutation.ExpectedOriginal) throw new Rejection("STALE_MUTATION");
            ValidateMark(intent.Mutation.NewValue, source.Generation);
            if (intent.Mutation.NewValue == intent.Mutation.ExpectedOriginal)
                throw new Rejection("INVALID_REQUEST");

            byte[] output;
            if (verify)
                output = Bytes(root, "output_base64");
            else
            {
                var clone = source.Clone();
                var changed = Target(clone, intent.Mutation).Clone();
                SetMark(changed, intent.Mutation.NewValue);
                changed.RefreshChecksum();
                ValidatePokemonDiff(before, changed, intent.Mutation);
                var offset = TargetOffset(clone, intent.Mutation);
                // Do not call import helpers: those may adjust handler, records,
                // forms, party stats or Pokedex. These native serialization APIs
                // write this exact PKM with its refreshed native checksum.
                if (intent.Mutation.Location == "box")
                    clone.WriteBoxSlot(changed, clone.Data.AsSpan(offset, StoredSize));
                else
                    clone.WritePartySlot(changed, clone.Data.AsSpan(offset, PartySize));
                output = clone.Write();
            }
            VerifyDiff(original, output, source, before, intent);
            return new
            {
                SchemaVersion = 1, WriterVersion, Status = verify ? "verified" : "prepared",
                Error = (string?)null, Game = intent.Game, intent.TrainerKey,
                SourceSha256 = Hash(original), OutputSha256 = Hash(output),
                OutputBase64 = verify ? null : Convert.ToBase64String(output),
                SemanticDiff = new
                {
                    intent.Mutation.Kind, intent.Mutation.Location, intent.Mutation.BoxIndex,
                    intent.Mutation.SlotIndex, intent.Mutation.ExpectedOriginal, intent.Mutation.NewValue,
                    PreservedUnrelated = true, ChecksumsValid = true, SignatureValid = true,
                },
            };
        }
        catch (Rejection e) { return Failure(e.Code); }
        catch (JsonException) { return Failure("INVALID_REQUEST"); }
        catch (FormatException) { return Failure("INVALID_REQUEST"); }
        catch (OverflowException) { return Failure("INVALID_REQUEST"); }
        catch (Exception) { return Failure("WRITE_PREPARATION_FAILED"); }
    }

    public static object Failure(string code) => new
    {
        SchemaVersion = 1, WriterVersion, Status = "rejected", Error = code,
        Game = (string?)null, TrainerKey = (string?)null, SourceSha256 = (string?)null,
        OutputSha256 = (string?)null, OutputBase64 = (string?)null, SemanticDiff = (object?)null,
    };

    internal static void Exact(JsonElement element, string[] names)
    {
        if (element.ValueKind != JsonValueKind.Object) throw new Rejection("INVALID_REQUEST");
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var item in element.EnumerateObject())
            if (!names.Contains(item.Name, StringComparer.Ordinal) || !seen.Add(item.Name))
                throw new Rejection("INVALID_REQUEST");
        if (seen.Count != names.Length) throw new Rejection("INVALID_REQUEST");
    }

    internal static string Text(JsonElement element, string key)
    {
        var value = element.GetProperty(key);
        if (value.ValueKind != JsonValueKind.String) throw new Rejection("INVALID_REQUEST");
        return value.GetString()!;
    }

    internal static int Integer(JsonElement element, string key)
    {
        var value = element.GetProperty(key);
        if (value.ValueKind != JsonValueKind.Number || !value.TryGetInt32(out var number))
            throw new Rejection("INVALID_REQUEST");
        return number;
    }

    internal static byte[] Bytes(JsonElement element, string key)
    {
        var text = Text(element, key);
        if (text.Length > 645000) throw new Rejection("INVALID_REQUEST");
        var bytes = Convert.FromBase64String(text);
        // Exact canonical base64, including padding; no whitespace variants.
        if (Convert.ToBase64String(bytes) != text) throw new Rejection("INVALID_REQUEST");
        if (bytes.Length is not (SaveUtil.SIZE_G6XY or SaveUtil.SIZE_G6ORAS or SaveUtil.SIZE_G7SM or SaveUtil.SIZE_G7USUM))
            throw new Rejection("UNSUPPORTED_FORMAT");
        return bytes;
    }

    private static Intent ParseIntent(JsonElement value)
    {
        Exact(value, ["game", "expected_sha256", "trainer_key", "mutation"]);
        var game = Text(value, "game");
        if (game is not ("X" or "Y" or "OR" or "AS" or "SN" or "MN" or "US" or "UM"))
            throw new Rejection("UNSUPPORTED_FORMAT");
        var sourceHash = Text(value, "expected_sha256");
        var trainerKey = Text(value, "trainer_key");
        foreach (var hash in new[] { sourceHash, trainerKey })
            if (hash.Length != 64 || hash.Any(c => !char.IsAsciiHexDigit(c) || char.IsUpper(c)))
                throw new Rejection("INVALID_REQUEST");
        var m = value.GetProperty("mutation");
        Exact(m, ["kind", "location", "box_index", "slot_index", "expected_original", "new_value"]);
        if (Text(m, "kind") != "test_marking") throw new Rejection("INVALID_REQUEST");
        var location = Text(m, "location");
        if (location is not ("box" or "party")) throw new Rejection("INVALID_REQUEST");
        var box = m.GetProperty("box_index");
        int? boxIndex = box.ValueKind == JsonValueKind.Null ? null : Integer(m, "box_index");
        if (location == "box" && boxIndex is null || location == "party" && boxIndex is not null)
            throw new Rejection("INVALID_REQUEST");
        return new Intent(game, sourceHash, trainerKey,
            new Mutation("test_marking", location, boxIndex, Integer(m, "slot_index"),
                Integer(m, "expected_original"), Integer(m, "new_value")));
    }

    internal static SAV_BEEF Validate(byte[] bytes)
    {
        // Inspection checks raw Gen7 signature binding BEFORE PKHeX clears its
        // signature buffer, as well as all occupied Pokemon and native checksums.
        var inspected = JsonSerializer.SerializeToElement(Inspection.Inspect(bytes), Inspection.Json);
        if (inspected.GetProperty("error").ValueKind != JsonValueKind.Null)
            throw new Rejection("CORRUPT_SAVE");
        var save = SaveUtil.GetVariantSAV((byte[])bytes.Clone());
        if (save is not (SAV6XY or SAV6AO or SAV7SM or SAV7USUM))
            throw new Rejection("UNSUPPORTED_FORMAT");
        if (bytes.Length != save.Data.Length || !save.ChecksumsValid)
            throw new Rejection("CORRUPT_SAVE");
        return (SAV_BEEF)save;
    }

    private static PKM Target(SaveFile save, Mutation mutation)
    {
        PKM pokemon;
        if (mutation.Location == "box")
        {
            if (mutation.BoxIndex is not { } box || box < 0 || box >= save.BoxCount
                || mutation.SlotIndex < 0 || mutation.SlotIndex >= save.BoxSlotCount
                || save.IsBoxSlotOverwriteProtected(box, mutation.SlotIndex))
                throw new Rejection("UNSAFE_TARGET");
            pokemon = save.GetBoxSlotAtIndex(box, mutation.SlotIndex);
        }
        else
        {
            if (mutation.SlotIndex < 0 || mutation.SlotIndex >= save.PartyCount)
                throw new Rejection("UNSAFE_TARGET");
            pokemon = save.GetPartySlotAtIndex(mutation.SlotIndex);
        }
        if (pokemon.Species == 0 || pokemon.IsEgg || !pokemon.ChecksumValid || pokemon is not G6PKM { Sanity: 0 })
            throw new Rejection("UNSAFE_TARGET");
        return pokemon;
    }

    private static int TargetOffset(SaveFile save, Mutation mutation)
        => mutation.Location == "box" ? save.GetBoxSlotOffset(mutation.BoxIndex!.Value, mutation.SlotIndex)
                                     : save.GetPartyOffset(mutation.SlotIndex);

    private static int Mark(PKM pokemon) => pokemon switch
    {
        PK6 p => p.MarkingValue,
        PK7 p => p.MarkingValue,
        _ => throw new Rejection("UNSUPPORTED_FORMAT"),
    };

    private static void ValidateMark(int value, int generation)
    {
        if (generation == 6 && value is >= 0 and <= 63) return;
        if (generation == 7 && value is >= 0 and <= 4095
            && Enumerable.Range(0, 6).All(i => ((value >> (i * 2)) & 3) < 3)) return;
        throw new Rejection("INVALID_REQUEST");
    }

    private static void SetMark(PKM pokemon, int value)
    {
        switch (pokemon)
        {
            case PK6 p: p.MarkingValue = (byte)value; break;
            case PK7 p: p.MarkingValue = (ushort)value; break;
            default: throw new Rejection("UNSUPPORTED_FORMAT");
        }
    }

    private static void ValidatePokemonDiff(PKM original, PKM changed, Mutation mutation)
    {
        if (original.GetType() != changed.GetType() || original.Data.Length != changed.Data.Length
            || !changed.ChecksumValid
            || Mark(changed) != mutation.NewValue)
            throw new Rejection("UNEXPECTED_DIFF");
        var markOffset = original is PK6 ? 0x2A : 0x16;
        var markLength = original is PK6 ? 1 : 2;
        for (int i = 0; i < original.Data.Length; i++)
        {
            if (original.Data[i] == changed.Data[i]) continue;
            if (i is 6 or 7 || i >= markOffset && i < markOffset + markLength) continue;
            throw new Rejection("UNEXPECTED_DIFF");
        }
    }

    private static void VerifyDiff(byte[] original, byte[] output, SAV_BEEF source, PKM before, Intent intent)
    {
        if (original.Length != output.Length || original.AsSpan().SequenceEqual(output))
            throw new Rejection("VERIFICATION_FAILED");
        var result = Validate(output);
        if (result.GetType() != source.GetType() || result.Version.ToString() != intent.Game
            || TrainerKey(result) != intent.TrainerKey)
            throw new Rejection("VERIFICATION_FAILED");
        var after = Target(result, intent.Mutation);
        ValidatePokemonDiff(before, after, intent.Mutation);
        var offset = TargetOffset(source, intent.Mutation);
        var length = intent.Mutation.Location == "box" ? StoredSize : PartySize;
        if (offset != TargetOffset(result, intent.Mutation)) throw new Rejection("UNEXPECTED_DIFF");
        // Only the containing block's two checksum bytes can change. The footer
        // metadata, block IDs/sizes, secure values, other block checksums and all
        // unknown/unprojected native bytes remain EXACTLY the same.
        var blocks = source.AllBlocks.Where(b => offset >= b.Offset && offset + length <= b.Offset + b.Length).ToArray();
        if (blocks.Length != 1) throw new Rejection("UNSUPPORTED_FORMAT");
        var checksum = original.Length - 0x200 + 0x14 + checked((int)blocks[0].ID * 8) + 6;
        var signature = source is SAV7USUM ? 0x6C000 + MemeCrypto.SaveFileSignatureOffset
                      : source is SAV7SM ? 0x6BA00 + MemeCrypto.SaveFileSignatureOffset : -1;
        for (int i = 0; i < original.Length; i++)
        {
            if (original[i] == output[i]) continue;
            if (i >= offset && i < offset + length || i == checksum || i == checksum + 1
                || signature >= 0 && i >= signature && i < signature + MemeCrypto.SaveFileSignatureLength)
                continue;
            throw new Rejection("UNEXPECTED_DIFF");
        }
        // Covers currently projected and private values in addition to the full
        // byte proof. Markings are not part of the reader DTO; its bytes/contract
        // therefore must be unchanged by this engineering-only operation.
        if (JsonSerializer.Serialize(Inspection.Inspect(original), Inspection.Json)
            != JsonSerializer.Serialize(Inspection.Inspect(output), Inspection.Json))
            throw new Rejection("UNEXPECTED_DIFF");
    }
}
