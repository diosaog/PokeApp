using PKHeX.Core;
using PokeApp.Parser;
using System.Security.Cryptography;
using System.Text.Json;
using static System.Buffers.Binary.BinaryPrimitives;

// Constructed native-format cases, never claimed as authentic gameplay saves.
internal static class SMChecks
{
    private static void Check(bool ok, string name)
    {
        if (!ok) throw new Exception(name);
        Console.WriteLine("PASS SM synthetic " + name);
    }
    private static JsonElement Read(byte[] bytes) => JsonSerializer.SerializeToElement(Inspection.Inspect(bytes), Inspection.Json);
    private static string? Error(byte[] bytes) => Read(bytes).GetProperty("error").GetString();
    public static void Run(string output)
    {
        foreach (var game in new[] { GameVersion.SN, GameVersion.MN })
        {
            var save = new SAV7SM { Version = game, OT = "SM Fixture", TID16 = 12345, SID16 = 54321, Language = 7, Gender = 1 };
            WriteUInt32LittleEndian(save.Data.AsSpan(save.Data.Length - 0x1F0), SaveUtil.BEEF);
            PK7 Pokemon(uint id, ushort species = 26, byte form = 1) => new()
            {
                Species = species, Form = form, PID = id, EncryptionConstant = id + 1000,
                OriginalTrainerName = "SM Fixture", TID16 = 12345, SID16 = 54321,
                Language = 7, Version = game, CurrentLevel = 42, Nickname = "Alola",
                HeldItem = 776, Move1 = 719, Move1_PP = 5, Ability = 207, Nature = Nature.Timid,
                IV_HP = 31, IV_SPE = 29, EV_SPE = 252, MetLevel = 5, MetLocation = 10,
            };
            save.PartyData = new PKM[] { Pokemon(123) };
            save.SetBoxSlotAtIndex(Pokemon(456, 741, 3), 0, 0);
            save.SetBoxSlotAtIndex(Pokemon(789, 778, 0), 7, 0);
            save.SetBoxSlotAtIndex(Pokemon(987, 802, 0), 31, 29);
            var bytes = save.Write();
            var hash = SHA256.HashData(bytes);
            var result = Read(bytes);
            Check(result.GetProperty("error").ValueKind == JsonValueKind.Null, game + " parsed: " + Error(bytes));
            var obs = result.GetProperty("observation");
            Check(obs.GetProperty("game").GetString() == game.ToString(), "content game identity");
            Check(obs.GetProperty("trainer").GetProperty("tid").GetInt32() == 12345, "original trainer IDs");
            var party = obs.GetProperty("party");
            Check(party.GetArrayLength() == 6 && party[1].ValueKind == JsonValueKind.Null, "party/empty slots");
            Check(party[0].GetProperty("form").GetInt32() == 1
                && party[0].GetProperty("type_ids")[0].GetInt32() == 12
                && party[0].GetProperty("type_ids")[1].GetInt32() == 13, "Alolan Raichu form/types");
            Check(party[0].GetProperty("identity").GetProperty("encryption_constant").GetUInt32() == 1123, "independent EC");
            Check(party[0].GetProperty("moves")[0].GetProperty("id").GetInt32() == 719, "SM move ceiling");
            var boxes = obs.GetProperty("boxes");
            Check(boxes.GetArrayLength() == 32 && boxes[31].GetProperty("slots")[29].GetProperty("species_id").GetInt32() == 802
                && boxes[7].GetProperty("slots")[0].ValueKind == JsonValueKind.Object, "last box/dead slot");
            Check(obs.GetProperty("progress").ValueKind == JsonValueKind.Null, "unknown progress");
            Check(Read(bytes).GetRawText() == result.GetRawText() && hash.SequenceEqual(SHA256.HashData(bytes)), "determinism/input unchanged");
            var folder = Path.Combine(output, "sm", game.ToString());
            Directory.CreateDirectory(folder);
            File.WriteAllBytes(Path.Combine(folder, "main"), bytes);
            save.Money = 77;
            File.WriteAllBytes(Path.Combine(folder, "later"), save.Write());
            var damaged = (byte[])bytes.Clone(); damaged[save.GetBoxOffset(0)] ^= 0x80;
            Check(Error(damaged) == "CORRUPT_SAVE", "PC checksum rejection");
            damaged = (byte[])bytes.Clone(); damaged[0x6BB00] ^= 0x80;
            Check(Error(damaged) == "CORRUPT_SAVE", "signature rejection");
            Check(Error(bytes[..^1]) is not null && Error(bytes[..100]) == "TRUNCATED_SAVE", "truncation rejection");
            var badMon = new SAV7SM((byte[])bytes.Clone());
            badMon.Data[badMon.GetBoxOffset(0) + 10] ^= 0x80;
            Check(Error(badMon.Write()) == "CORRUPT_SAVE", "inner checksum rejection");
            save.Version = GameVersion.US;
            Check(Error(save.Write()) == "UNSUPPORTED_VERSION", "US ID in SM layout rejected");
            save.Version = game;
            save.PartyData = new PKM[] { Pokemon(123, 26, 255) };
            Check(Error(save.Write()) == "CORRUPT_SAVE", "invalid form rejection");
        }
        var sm = new SAV7SM();
        Check(sm.MaxSpeciesID == 802 && sm.MaxMoveID == 719 && sm.MaxItemID == 920 && sm.MaxAbilityID == 232, "pinned SM ceilings");
        foreach (var game in new[] { GameVersion.US, GameVersion.UM })
        {
            var usum = new SAV7USUM { Version = game };
            WriteUInt32LittleEndian(usum.Data.AsSpan(usum.Data.Length - 0x1F0), SaveUtil.BEEF);
            Check(Error(usum.Write()) == "UNSUPPORTED_GAME", "USUM rejected " + game);
        }
    }
}
