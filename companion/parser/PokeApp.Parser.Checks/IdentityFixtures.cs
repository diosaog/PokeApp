using PKHeX.Core;
using PokeApp.Parser;
using System.Security.Cryptography;
using System.Text.Json;
using static System.Buffers.Binary.BinaryPrimitives;

// Deterministic synthetic native snapshots for local identity integration tests.
// No source save is opened or changed; these are not gameplay-stage evidence.
internal static class IdentityFixtures
{
    private static void Check(bool condition, string label)
    {
        if (!condition) throw new Exception(label);
        Console.WriteLine("PASS identity fixture " + label);
    }

    private static SaveFile Save(GameVersion game)
    {
        SaveFile save = game switch
        {
            GameVersion.X or GameVersion.Y => new SAV6XY(),
            GameVersion.OR or GameVersion.AS => new SAV6AO(),
            GameVersion.SN or GameVersion.MN => new SAV7SM(),
            _ => new SAV7USUM(),
        };
        save.Version = game; save.OT = "Fixture"; save.TID16 = 12345;
        save.SID16 = 6789; save.Language = 2; save.Gender = 0;
        WriteUInt32LittleEndian(save.Data.AsSpan(save.Data.Length - 0x1F0), SaveUtil.BEEF);
        return save;
    }

    private static PKM Pokemon(SaveFile save)
    {
        var p = save.BlankPKM;
        p.Species = 1; p.Version = save.Version; p.PID = 123456789;
        p.EncryptionConstant = 987654321; p.TID16 = save.TID16; p.SID16 = save.SID16;
        p.OriginalTrainerName = save.OT; p.OriginalTrainerGender = save.Gender; p.Language = save.Language;
        p.CurrentLevel = 5; p.Nickname = "Before"; p.Move1 = 33; p.Move1_PP = 35;
        p.Ability = 65; p.Nature = Nature.Hardy; p.MetLocation = 10; p.MetLevel = 5;
        p.MetDate = new DateOnly(2026, 1, 2); p.EggLocation = 0;
        p.IV_HP = 17; p.IV_ATK = 2; p.IV_DEF = 3; p.IV_SPA = 4; p.IV_SPD = 5; p.IV_SPE = 6;
        p.RefreshChecksum();
        return p;
    }

    private static JsonElement Write(SaveFile save, string folder, string name, List<object> manifest)
    {
        Directory.CreateDirectory(folder);
        var bytes = save.Write();
        var hash = SHA256.HashData(bytes);
        var parsed = JsonSerializer.SerializeToElement(Inspection.Inspect(bytes), Inspection.Json);
        Check(parsed.GetProperty("error").ValueKind == JsonValueKind.Null, save.Version + " " + name + " native accepted");
        Check(hash.SequenceEqual(SHA256.HashData(bytes)), save.Version + " " + name + " reader leaves input unchanged");
        var path = Path.Combine(folder, name);
        File.WriteAllBytes(path, bytes);
        manifest.Add(new { Game = save.Version.ToString(), File = Path.Combine(Path.GetFileName(folder), name),
            Sha256 = Convert.ToHexString(hash).ToLowerInvariant(), Synthetic = true });
        return parsed.GetProperty("observation");
    }

    public static void Run(string output)
    {
        var manifest = new List<object>();
        foreach (var game in new[] { GameVersion.X, GameVersion.Y, GameVersion.OR, GameVersion.AS, GameVersion.SN, GameVersion.MN, GameVersion.US, GameVersion.UM })
        {
            var save = Save(game); var p = Pokemon(save);
            save.PartyData = new[] { p };
            var folder = Path.Combine(output, game.ToString());
            var before = Write(save, folder, "main", manifest);
            var identity = before.GetProperty("party")[0].GetProperty("identity");
            Check(identity.GetProperty("ot_name").GetString() == before.GetProperty("trainer").GetProperty("name").GetString()
                && identity.GetProperty("met_date").GetString() == "2026-01-02"
                && identity.GetProperty("egg_location").GetInt32() == 0
                && identity.GetProperty("egg_date").ValueKind == JsonValueKind.Null,
                game + " complete non-egg matching-OT native evidence for trusted schema2 conversion");
            var later = p.Clone(); later.Species = 2; later.CurrentLevel = 20;
            later.Nickname = "After"; later.Move1 = 73; later.Move1_PP = 10; later.HeldItem = 234;
            later.RefreshChecksum();
            save.PartyData = Array.Empty<PKM>(); save.SetBoxSlotAtIndex(later, 7, 29);
            var after = Write(save, folder, "later", manifest);
            var moved = after.GetProperty("boxes")[7].GetProperty("slots")[29];
            Check(moved.GetProperty("identity").GetRawText() == identity.GetRawText()
                && moved.GetProperty("species_id").GetInt32() == 2
                && after.GetProperty("party").EnumerateArray().All(s => s.ValueKind == JsonValueKind.Null),
                game + " evolution and visible changes plus party to Box8 slot30 preserve all native identity facts");
            if (game != GameVersion.X) continue;

            var variant = Save(game); variant.PartyData = new[] { p, p.Clone() };
            Write(variant, folder, "clone", manifest);
            variant.PartyData = Array.Empty<PKM>(); variant.SetBoxSlotAtIndex(p, 2, 3);
            Write(variant, folder, "clone-singleton", manifest);
            variant = Save(game); var replacement = p.Clone(); replacement.PID = 11223344;
            replacement.EncryptionConstant = 55667788; replacement.RefreshChecksum();
            variant.PartyData = new[] { replacement };
            Write(variant, folder, "replacement", manifest);
            variant = Save(game); var egg = p.Clone(); egg.IsEgg = true;
            egg.EggLocation = 60002; egg.EggMetDate = new DateOnly(2026, 1, 1); egg.RefreshChecksum();
            variant.PartyData = new[] { egg };
            Write(variant, folder, "egg", manifest);
            variant = Save(game); var collision = p.Clone(); collision.EncryptionConstant = 1234; collision.RefreshChecksum();
            variant.PartyData = new[] { p, collision };
            Write(variant, folder, "collision", manifest);
        }
        File.WriteAllText(Path.Combine(output, "manifest.json"), JsonSerializer.Serialize(new
        {
            Kind = "synthetic_native_identity_fixtures", SchemaVersion = 1,
            Note = "Created from blank PKHeX objects. Not authentic gameplay evidence. Native schema1 identity is converted to trusted schema2 only by the authorized ingestion layer.",
            Files = manifest,
        }, Inspection.Json));
        Console.WriteLine("RESULT OK; synthetic native identity fixtures for eight games");
    }
}
