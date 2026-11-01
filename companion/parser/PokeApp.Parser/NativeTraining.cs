using PKHeX.Core;
using System.Security.Cryptography;
using System.Text.Json;
using static PokeApp.Parser.NativeWrite;

namespace PokeApp.Parser;

// PokeApp virtual consumables change actual Nature/IV data, never a bag item or
// Hyper Training flag. Competitive authority, death-box rules and consumption
// remain server-owned. This component transforms bytes without opening files.
public static class NativeTraining
{
    private const int StoredSize = 232, PartySize = 260;
    private sealed record Location(string Name, int? Box, int Slot);
    private sealed record Mutation(string Item, string Attempt, Location At, string ExpectedPokemonSha256,
        int ExpectedNature, int[] ExpectedIvs, int? NatureId, string? Stat);
    private static readonly string[] Games = ["X", "Y", "OR", "AS", "SN", "MN", "US", "UM"];
    private static readonly string[] Stats = ["hp", "atk", "defense", "spa", "spd", "spe"];

    public static object Inspect(ReadOnlySpan<byte> request)
    {
        try
        {
            if (request.Length is 0 or > MaxRequestBytes) throw new Rejection("INVALID_REQUEST");
            using var document = JsonDocument.Parse(request.ToArray(), new JsonDocumentOptions { MaxDepth = 8 });
            var root = document.RootElement;
            Exact(root, ["schema_version", "source_base64", "location", "box_index", "slot_index"]);
            if (Integer(root, "schema_version") != 1) throw new Rejection("INVALID_REQUEST");
            var bytes = Bytes(root, "source_base64");
            var save = Validate(bytes);
            var at = ParseLocation(root);
            var pokemon = Target(save, at);
            return new
            {
                SchemaVersion = 1, WriterVersion, Status = "inspected", Error = (string?)null,
                Game = save.Version.ToString(), TrainerKey = NativeWrite.TrainerKey(save),
                SourceSha256 = Hash(bytes), OutputSha256 = (string?)null, OutputBase64 = (string?)null,
                SemanticDiff = new
                {
                    Location = at.Name, BoxIndex = at.Box, SlotIndex = at.Slot,
                    PokemonSha256 = PokemonHash(pokemon), Nature = (int)pokemon.Nature, Ivs = Ivs(pokemon),
                    TargetPid = pokemon.PID, TargetEc = pokemon.EncryptionConstant, pokemon.IsEgg,
                    LegalityWarnings = Array.Empty<string>(), HiddenPowerType = pokemon.HPType,
                },
            };
        }
        catch (Rejection e) { return Failure(e.Code); }
        catch (JsonException) { return Failure("INVALID_REQUEST"); }
        catch (FormatException) { return Failure("INVALID_REQUEST"); }
        catch (OverflowException) { return Failure("INVALID_REQUEST"); }
        catch (Exception) { return Failure("TRAINING_INSPECTION_FAILED"); }
    }

    internal static object Execute(JsonElement root, bool verify)
    {
        var intent = root.GetProperty("intent");
        Exact(intent, ["game", "expected_sha256", "trainer_key", "mutation"]);
        string game = Text(intent, "game"), trainer = Text(intent, "trainer_key"), expectedHash = Text(intent, "expected_sha256");
        if (!Games.Contains(game, StringComparer.Ordinal)) throw new Rejection("UNSUPPORTED_FORMAT");
        RequireHash(trainer); RequireHash(expectedHash);
        var m = ParseMutation(intent.GetProperty("mutation"));
        var original = Bytes(root, "source_base64");
        var source = Validate(original);
        if (Hash(original) != expectedHash) throw new Rejection("STALE_SOURCE");
        if (source.Version.ToString() != game) throw new Rejection("WRONG_GAME");
        if (NativeWrite.TrainerKey(source) != trainer) throw new Rejection("WRONG_TRAINER");
        var before = Target(source, m.At);
        if (PokemonHash(before) != m.ExpectedPokemonSha256 || (int)before.Nature != m.ExpectedNature
            || !Ivs(before).SequenceEqual(m.ExpectedIvs)) throw new Rejection("STALE_MUTATION");

        var changed = before.Clone();
        Apply(changed, m);
        if (m.At.Name == "party") UpdateDependentStats(before, changed);
        changed.RefreshChecksum();
        ValidatePokemonDiff(before, changed, m);
        // Randomized/private saves are intentional. Official encounter,
        // learnset, ability and event legality does not authorize this change.
        // The exact native diff and structural checks below are the authority.

        var clone = source.Clone();
        int offset = Offset(clone, m.At), length = m.At.Name == "box" ? StoredSize : PartySize;
        if (m.At.Name == "box") clone.WriteBoxSlot(changed, clone.Data.AsSpan(offset, StoredSize));
        else clone.WritePartySlot(changed, clone.Data.AsSpan(offset, PartySize));
        var expected = clone.Write();
        NormalizeGeneratedSignature(expected, source);
        var output = verify ? Bytes(root, "output_base64") : expected;
        if (original.Length != output.Length || original.AsSpan().SequenceEqual(output)
            || !expected.AsSpan().SequenceEqual(output)) throw new Rejection("UNEXPECTED_DIFF");
        var result = Validate(output);
        if (result.GetType() != source.GetType() || result.Version.ToString() != game
            || NativeWrite.TrainerKey(result) != trainer || Offset(result, m.At) != offset)
            throw new Rejection("VERIFICATION_FAILED");
        var after = Target(result, m.At);
        ValidatePokemonDiff(before, after, m);
        if (!after.Data.AsSpan().SequenceEqual(changed.Data)) throw new Rejection("UNEXPECTED_DIFF");
        VerifySaveDiff(original, output, source, offset, length);
        return new
        {
            SchemaVersion = 1, WriterVersion, Status = verify ? "verified" : "prepared", Error = (string?)null,
            Game = game, TrainerKey = trainer, SourceSha256 = Hash(original), OutputSha256 = Hash(output),
            OutputBase64 = verify ? null : Convert.ToBase64String(output),
            SemanticDiff = new
            {
                Kind = "virtual_training", ItemCode = m.Item, m.Attempt, Location = m.At.Name, BoxIndex = m.At.Box, SlotIndex = m.At.Slot,
                m.ExpectedPokemonSha256, m.ExpectedNature, m.ExpectedIvs, m.NatureId, m.Stat,
                BeforeNature = (int)before.Nature, AfterNature = (int)after.Nature,
                BeforeIvs = Ivs(before), AfterIvs = Ivs(after), TargetPid = before.PID, TargetEc = before.EncryptionConstant,
                BeforePokemonSha256 = PokemonHash(before), AfterPokemonSha256 = PokemonHash(after),
                LegalityWarningsBefore = Array.Empty<string>(), LegalityWarningsAfter = Array.Empty<string>(),
                HiddenPowerBefore = before.HPType, HiddenPowerAfter = after.HPType,
                PreservedUnrelated = true, ChecksumsValid = true, SignatureValid = true,
            },
        };
    }

    private static Mutation ParseMutation(JsonElement m)
    {
        Exact(m, ["kind", "item_code", "attempt", "location", "box_index", "slot_index", "expected_pokemon_sha256",
            "expected_nature", "expected_ivs", "nature_id", "stat"]);
        if (Text(m, "kind") != "virtual_training") throw new Rejection("INVALID_REQUEST");
        var item = Text(m, "item_code");
        if (item is not ("menta_naturaleza" or "chapa_plateada" or "chapa_dorada")) throw new Rejection("INVALID_REQUEST");
        var attempt = Text(m, "attempt");
        if (!Guid.TryParseExact(attempt, "D", out var operation) || operation == Guid.Empty || operation.ToString("D") != attempt)
            throw new Rejection("INVALID_REQUEST");
        var hash = Text(m, "expected_pokemon_sha256"); RequireHash(hash);
        int nature = Integer(m, "expected_nature");
        var ivs = m.GetProperty("expected_ivs");
        if (nature is < 0 or > 24 || ivs.ValueKind != JsonValueKind.Array || ivs.GetArrayLength() != 6)
            throw new Rejection("INVALID_REQUEST");
        var values = ivs.EnumerateArray().Select(v => v.ValueKind == JsonValueKind.Number && v.TryGetInt32(out int n)
            && n is >= 0 and <= 31 ? n : throw new Rejection("INVALID_REQUEST")).ToArray();
        int? natureId = m.GetProperty("nature_id").ValueKind == JsonValueKind.Null ? null : Integer(m, "nature_id");
        string? stat = m.GetProperty("stat").ValueKind == JsonValueKind.Null ? null : Text(m, "stat");
        if (item == "menta_naturaleza" ? natureId is null or < 0 or > 24 || stat is not null
            : item == "chapa_plateada" ? natureId is not null || stat is null || !Stats.Contains(stat, StringComparer.Ordinal)
            : natureId is not null || stat is not null) throw new Rejection("INVALID_REQUEST");
        return new(item, attempt, ParseLocation(m), hash, nature, values, natureId, stat);
    }

    private static Location ParseLocation(JsonElement value)
    {
        string location = Text(value, "location");
        int? box = value.GetProperty("box_index").ValueKind == JsonValueKind.Null ? null : Integer(value, "box_index");
        int slot = Integer(value, "slot_index");
        if (location is not ("box" or "party") || location == "box" && box is null
            || location == "party" && box is not null) throw new Rejection("INVALID_REQUEST");
        return new(location, box, slot);
    }

    private static void RequireHash(string hash)
    {
        if (hash.Length != 64 || hash.Any(c => !char.IsAsciiHexDigit(c) || char.IsUpper(c)))
            throw new Rejection("INVALID_REQUEST");
    }

    private static PKM Target(SaveFile save, Location at)
    {
        PKM pokemon;
        if (at.Name == "box")
        {
            if (at.Box is not { } b || b < 0 || b >= save.BoxCount || at.Slot < 0 || at.Slot >= save.BoxSlotCount
                || save.IsBoxSlotOverwriteProtected(b, at.Slot)) throw new Rejection("UNSAFE_TARGET");
            pokemon = save.GetBoxSlotAtIndex(b, at.Slot);
        }
        else
        {
            if (at.Slot < 0 || at.Slot >= save.PartyCount) throw new Rejection("UNSAFE_TARGET");
            pokemon = save.GetPartySlotAtIndex(at.Slot);
        }
        if (pokemon.Species == 0 || pokemon.Species > pokemon.MaxSpeciesID || pokemon.Species > save.MaxSpeciesID
            || !save.Personal.IsPresentInGame(pokemon.Species, pokemon.Form) || (int)pokemon.Nature is < 0 or > 24
            || pokemon.IsEgg || !pokemon.ChecksumValid
            || pokemon is not (PK6 or PK7) || pokemon is not G6PKM { Sanity: 0 }) throw new Rejection("UNSAFE_TARGET");
        return pokemon;
    }

    private static int Offset(SaveFile save, Location at) => at.Name == "box"
        ? save.GetBoxSlotOffset(at.Box!.Value, at.Slot) : save.GetPartyOffset(at.Slot);
    private static string PokemonHash(PKM p) => Hash(p.DecryptedBoxData);
    private static int[] Ivs(PKM p) => [p.IV_HP, p.IV_ATK, p.IV_DEF, p.IV_SPA, p.IV_SPD, p.IV_SPE];

    private static void Apply(PKM p, Mutation m)
    {
        if (m.Item == "menta_naturaleza")
        {
            if ((int)p.Nature == m.NatureId) throw new Rejection("TRAINING_NO_CHANGE");
            p.Nature = (Nature)m.NatureId!.Value;
            return;
        }
        var values = Ivs(p);
        if (m.Item == "chapa_dorada") Array.Fill(values, 31);
        else values[Array.IndexOf(Stats, m.Stat!)] = 31;
        if (values.SequenceEqual(Ivs(p))) throw new Rejection("TRAINING_NO_CHANGE");
        p.IV_HP = values[0]; p.IV_ATK = values[1]; p.IV_DEF = values[2];
        p.IV_SPA = values[3]; p.IV_SPD = values[4]; p.IV_SPE = values[5];
    }

    private static void UpdateDependentStats(PKM before, PKM after)
    {
        var oldStats = before.GetStats(before.PersonalInfo);
        var newStats = after.GetStats(after.PersonalInfo);
        // PKHeX stat order differs from the public IV order: H/A/D/S/SpA/SpD.
        // Never use ResetPartyStats: that heals HP and clears status conditions.
        if (oldStats[0] != newStats[0]) after.Stat_HPMax = newStats[0];
        if (oldStats[1] != newStats[1]) after.Stat_ATK = newStats[1];
        if (oldStats[2] != newStats[2]) after.Stat_DEF = newStats[2];
        if (oldStats[3] != newStats[3]) after.Stat_SPE = newStats[3];
        if (oldStats[4] != newStats[4]) after.Stat_SPA = newStats[4];
        if (oldStats[5] != newStats[5]) after.Stat_SPD = newStats[5];
    }

    private static void ValidatePokemonDiff(PKM before, PKM after, Mutation m)
    {
        if (before.GetType() != after.GetType() || before.Data.Length != after.Data.Length || !after.ChecksumValid)
            throw new Rejection("UNEXPECTED_DIFF");
        var expected = before.Clone();
        Apply(expected, m);
        if (m.At.Name == "party") UpdateDependentStats(before, expected);
        expected.RefreshChecksum();
        if (!expected.Data.AsSpan().SequenceEqual(after.Data)) throw new Rejection("UNEXPECTED_DIFF");
        for (int i = 0; i < before.Data.Length; i++)
        {
            if (before.Data[i] == after.Data[i] || i is 6 or 7) continue;
            if (m.Item == "menta_naturaleza" && i == 0x1C) continue;
            if (m.Item != "menta_naturaleza" && i is >= 0x74 and <= 0x77) continue;
            if (m.At.Name == "party" && i is >= 0xF2 and <= 0xFD) continue;
            throw new Rejection("UNEXPECTED_DIFF");
        }
    }

    private static void VerifySaveDiff(byte[] original, byte[] output, SAV_BEEF source, int offset, int length)
    {
        var blocks = source.AllBlocks.Where(b => offset >= b.Offset && offset + length <= b.Offset + b.Length).ToArray();
        if (blocks.Length != 1) throw new Rejection("UNSUPPORTED_FORMAT");
        int checksum = original.Length - 0x200 + 0x14 + checked((int)blocks[0].ID * 8) + 6;
        int signature = source is SAV7USUM ? 0x6C000 + MemeCrypto.SaveFileSignatureOffset
            : source is SAV7SM ? 0x6BA00 + MemeCrypto.SaveFileSignatureOffset : -1;
        for (int i = 0; i < original.Length; i++)
            if (original[i] != output[i] && !(i >= offset && i < offset + length || i == checksum || i == checksum + 1
                || signature >= 0 && i >= signature && i < signature + MemeCrypto.SaveFileSignatureLength))
                throw new Rejection("UNEXPECTED_DIFF");
    }

    private static void NormalizeGeneratedSignature(byte[] output, SaveFile source)
    {
        if (source is not SAV7) return;
        int start = (source is SAV7USUM ? 0x6C000 : 0x6BA00) + MemeCrypto.SaveFileSignatureOffset;
        var signature = output.AsSpan(start, MemeCrypto.SaveFileSignatureLength);
        var tableHash = SHA256.HashData(output.AsSpan(output.Length - 0x200, source is SAV7USUM ? 0x150 : 0x140));
        bool Valid(ReadOnlySpan<byte> value) => NativeSignature.Verify(value, tableHash);
        if (Valid(signature)) return;
        // PKHeX 24.11.11 writes a short big-endian RSA result at the START of
        // its fixed buffer instead of left-padding it. Re-align only the known
        // RSA suffix, accepting a candidate solely after the existing full
        // cryptographic signature and checksum-table binding both verify.
        var raw = signature.ToArray();
        var candidate = raw.ToArray();
        const int rsaBytes = 96, rsaStart = MemeCrypto.SaveFileSignatureLength - rsaBytes;
        for (int padding = 1; padding < rsaBytes; padding++)
        {
            candidate.AsSpan(rsaStart, rsaBytes).Clear();
            raw.AsSpan(rsaStart, rsaBytes - padding).CopyTo(candidate.AsSpan(rsaStart + padding));
            if (!Valid(candidate)) continue;
            candidate.CopyTo(signature);
            return;
        }
        throw new Rejection("CORRUPT_SAVE");
    }
}
