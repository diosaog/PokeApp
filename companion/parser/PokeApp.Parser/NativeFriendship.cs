using PKHeX.Core;
using System.Text.Json;
using static PokeApp.Parser.NativeWrite;

namespace PokeApp.Parser;

// «Felicidad máxima» (owner request 2026-11-04): one current-party Pokémon's
// real friendship becomes 255. Gen 6/7 keep two friendship bytes; the game
// reads the current handler's (PKHeX CurrentFriendship): Original Trainer at
// 0xCA, or Handling Trainer at 0xA2 for a Pokémon held by someone else.
// Pokémon-Amie affection (0xCB / 0xA3) and every other byte stay unchanged.
// Randomized species, moves and abilities are intentional: no legality or
// suggestion API is consulted, nothing is normalized. Structure, encryption,
// checksums, slot identity and the exact save diff are the authority.
// This component transforms bytes only: it never opens or writes a file.
public static class NativeFriendship
{
    public const int Max = 255;
    private const int PartySize = 260, OriginalFriendship = 0xCA, HandlerFriendship = 0xA2;
    private static readonly string[] Games = ["X", "Y", "OR", "AS", "SN", "MN", "US", "UM"];
    private sealed record Mutation(int Slot, string ExpectedPokemonSha256, int ExpectedFriendship);

    public static object Inspect(ReadOnlySpan<byte> request)
    {
        try
        {
            if (request.Length is 0 or > MaxRequestBytes) throw new Rejection("INVALID_REQUEST");
            using var document = JsonDocument.Parse(request.ToArray(), new JsonDocumentOptions { MaxDepth = 8 });
            var root = document.RootElement;
            Exact(root, ["schema_version", "source_base64"]);
            if (Integer(root, "schema_version") != 1) throw new Rejection("INVALID_REQUEST");
            var bytes = Bytes(root, "source_base64");
            var save = Validate(bytes);
            if (!Games.Contains(save.Version.ToString(), StringComparer.Ordinal)) throw new Rejection("UNSUPPORTED_FORMAT");
            var party = Enumerable.Range(0, save.PartyCount).Select(slot =>
            {
                var p = save.GetPartySlotAtIndex(slot);
                bool eligible = Eligible(save, p);
                return new
                {
                    SlotIndex = slot, Species = (int)p.Species, Form = (int)p.Form,
                    Nickname = eligible ? p.Nickname : "", Level = eligible ? (int)p.CurrentLevel : 0,
                    Friendship = eligible ? (int)p.CurrentFriendship : 0, Eligible = eligible,
                    PokemonSha256 = Hash(p.DecryptedBoxData),
                };
            }).ToArray();
            return new
            {
                SchemaVersion = 1, WriterVersion, Status = "inspected", Error = (string?)null,
                Game = save.Version.ToString(), TrainerKey = NativeWrite.TrainerKey(save),
                SourceSha256 = Hash(bytes), OutputSha256 = (string?)null, OutputBase64 = (string?)null,
                SemanticDiff = new { Party = party },
            };
        }
        catch (Rejection e) { return Failure(e.Code); }
        catch (JsonException) { return Failure("INVALID_REQUEST"); }
        catch (FormatException) { return Failure("INVALID_REQUEST"); }
        catch (OverflowException) { return Failure("INVALID_REQUEST"); }
        catch (Exception) { return Failure("FRIENDSHIP_INSPECTION_FAILED"); }
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
        if (m.Slot >= source.PartyCount) throw new Rejection("UNSAFE_TARGET");
        var before = source.GetPartySlotAtIndex(m.Slot);
        if (!Eligible(source, before)) throw new Rejection("UNSAFE_TARGET");
        if (Hash(before.DecryptedBoxData) != m.ExpectedPokemonSha256 || before.CurrentFriendship != m.ExpectedFriendship)
            throw new Rejection("STALE_MUTATION");
        if (before.CurrentFriendship == Max) throw new Rejection("FRIENDSHIP_ALREADY_MAX");

        var changed = before.Clone();
        changed.CurrentFriendship = Max;
        changed.RefreshChecksum();
        ValidatePokemonDiff(before, changed);

        var clone = source.Clone();
        int offset = clone.GetPartyOffset(m.Slot);
        // Native serialization of this exact PKM only: no import helper may
        // adjust handler, records, forms, party stats or the Pokédex.
        clone.WritePartySlot(changed, clone.Data.AsSpan(offset, PartySize));
        var expected = clone.Write();
        NativeTraining.NormalizeGeneratedSignature(expected, source);
        var output = verify ? Bytes(root, "output_base64") : expected;
        if (original.Length != output.Length || original.AsSpan().SequenceEqual(output)
            || !expected.AsSpan().SequenceEqual(output)) throw new Rejection("UNEXPECTED_DIFF");
        var result = Validate(output);
        if (result.GetType() != source.GetType() || result.Version.ToString() != game
            || NativeWrite.TrainerKey(result) != trainer || result.PartyCount != source.PartyCount
            || result.GetPartyOffset(m.Slot) != offset) throw new Rejection("VERIFICATION_FAILED");
        var after = result.GetPartySlotAtIndex(m.Slot);
        ValidatePokemonDiff(before, after);
        if (after.CurrentFriendship != Max || !after.Data.AsSpan().SequenceEqual(changed.Data))
            throw new Rejection("UNEXPECTED_DIFF");
        for (int slot = 0; slot < source.PartyCount; slot++)
            if (slot != m.Slot && !source.GetPartySlotAtIndex(slot).Data.AsSpan().SequenceEqual(result.GetPartySlotAtIndex(slot).Data))
                throw new Rejection("UNEXPECTED_DIFF");
        NativeTraining.VerifySaveDiff(original, output, source, offset, PartySize);
        return new
        {
            SchemaVersion = 1, WriterVersion, Status = verify ? "verified" : "prepared", Error = (string?)null,
            Game = game, TrainerKey = trainer, SourceSha256 = Hash(original), OutputSha256 = Hash(output),
            OutputBase64 = verify ? null : Convert.ToBase64String(output),
            SemanticDiff = new
            {
                Kind = "max_friendship", Location = "party", SlotIndex = m.Slot,
                m.ExpectedPokemonSha256, m.ExpectedFriendship,
                PreservedUnrelated = true, ChecksumsValid = true, SignatureValid = true,
            },
        };
    }

    // Any real species/form of this game, encrypted and checksummed as the game
    // expects. A randomized moveset or ability is not a reason to refuse.
    private static bool Eligible(SaveFile save, PKM p)
        => p.Species != 0 && p.Species <= p.MaxSpeciesID && p.Species <= save.MaxSpeciesID
           && save.Personal.IsPresentInGame(p.Species, p.Form) && !p.IsEgg && p.ChecksumValid
           && p is PK6 or PK7 && p is G6PKM { Sanity: 0 } && p.CurrentHandler is 0 or 1;

    // Exactly the current handler's friendship byte (and the PKM checksum)
    // may differ; affection, the other handler's friendship and all else match.
    internal static void ValidatePokemonDiff(PKM before, PKM after)
    {
        if (before.GetType() != after.GetType() || before.Data.Length != after.Data.Length || !after.ChecksumValid
            || after.CurrentHandler != before.CurrentHandler) throw new Rejection("UNEXPECTED_DIFF");
        int field = before.CurrentHandler == 0 ? OriginalFriendship : HandlerFriendship;
        if (after.Data[field] != Max || after.CurrentFriendship != Max) throw new Rejection("UNEXPECTED_DIFF");
        for (int i = 0; i < before.Data.Length; i++)
            if (before.Data[i] != after.Data[i] && i is not (6 or 7) && i != field) throw new Rejection("UNEXPECTED_DIFF");
    }

    private static Mutation ParseMutation(JsonElement m)
    {
        Exact(m, ["kind", "location", "slot_index", "expected_pokemon_sha256", "expected_friendship"]);
        if (Text(m, "kind") != "max_friendship" || Text(m, "location") != "party") throw new Rejection("INVALID_REQUEST");
        int slot = Integer(m, "slot_index"), friendship = Integer(m, "expected_friendship");
        var hash = Text(m, "expected_pokemon_sha256"); RequireHash(hash);
        if (slot is < 0 or > 5 || friendship is < 0 or > Max) throw new Rejection("INVALID_REQUEST");
        return new(slot, hash, friendship);
    }

    private static void RequireHash(string hash)
    {
        if (hash.Length != 64 || hash.Any(c => !char.IsAsciiHexDigit(c) || char.IsUpper(c)))
            throw new Rejection("INVALID_REQUEST");
    }
}
