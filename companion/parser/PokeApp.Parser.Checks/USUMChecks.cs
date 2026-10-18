using PKHeX.Core;
using PokeApp.Parser;
using System.Security.Cryptography;
using System.Text.Json;
using static System.Buffers.Binary.BinaryPrimitives;

// Constructed native-format edge cases; public gameplay is a separate gate.
internal static class USUMChecks
{
    private static void Check(bool ok, string name)
    {
        if (!ok) throw new Exception(name);
        Console.WriteLine("PASS USUM synthetic " + name);
    }
    private static JsonElement Read(byte[] bytes) => JsonSerializer.SerializeToElement(Inspection.Inspect(bytes), Inspection.Json);
    private static string? Error(byte[] bytes) => Read(bytes).GetProperty("error").GetString();
    public static void Run(string output)
    {
        var limits = new SAV7USUM();
        Check(limits.MaxSpeciesID == 807 && limits.MaxMoveID == 728 && limits.MaxItemID == 959 && limits.MaxAbilityID == 233, "pinned USUM ceilings");
        foreach (var game in new[] { GameVersion.US, GameVersion.UM })
        {
            var save = new SAV7USUM { Version = game, OT = "Ultra Fixture", TID16 = 12345, SID16 = 54321, Language = 7, Gender = 1 };
            WriteUInt32LittleEndian(save.Data.AsSpan(save.Data.Length - 0x1F0), SaveUtil.BEEF);
            PK7 Pokemon(uint id, ushort species = 800, byte form = 1) => new()
            {
                Species = species, Form = form, PID = id, EncryptionConstant = id + 1000,
                OriginalTrainerName = "Ultra Fixture", TID16 = 12345, SID16 = 54321,
                Language = 7, Version = game, CurrentLevel = 42, Nickname = "Ultra",
                HeldItem = 923, Move1 = 728, Move1_PP = 5, Ability = 233, Nature = Nature.Timid,
                IV_HP = 31, IV_SPE = 29, EV_SPE = 252, MetLevel = 5, MetLocation = 10,
            };
            save.PartyData = new PKM[] { Pokemon(123), Pokemon(124, 800, 2) };
            save.SetBoxSlotAtIndex(Pokemon(456, 744, 1), 0, 0);
            save.SetBoxSlotAtIndex(Pokemon(789, 745, 2), 7, 0);
            save.SetBoxSlotAtIndex(Pokemon(987, 807, 0), 31, 29);
            var bytes = save.Write();
            var hash = SHA256.HashData(bytes);
            var result = Read(bytes);
            Check(result.GetProperty("error").ValueKind == JsonValueKind.Null, game + " parsed: " + Error(bytes));
            var obs = result.GetProperty("observation");
            Check(obs.GetProperty("game").GetString() == game.ToString(), "content game identity");
            Check(obs.GetProperty("trainer").GetProperty("tid").GetInt32() == 12345, "trainer mapping");
            var party = obs.GetProperty("party");
            Check(party.GetArrayLength() == 6 && party[2].ValueKind == JsonValueKind.Null, "party/empty slots");
            Check(party[0].GetProperty("form").GetInt32() == 1
                && party[0].GetProperty("type_ids")[0].GetInt32() == 13
                && party[0].GetProperty("type_ids")[1].GetInt32() == 8, "Dusk Mane types");
            Check(party[1].GetProperty("form").GetInt32() == 2
                && party[1].GetProperty("type_ids")[1].GetInt32() == 7, "Dawn Wings types");
            Check(party[0].GetProperty("identity").GetProperty("encryption_constant").GetUInt32() == 1123, "independent EC");
            var boxes = obs.GetProperty("boxes");
            Check(boxes.GetArrayLength() == 32 && boxes[31].GetProperty("slots")[29].GetProperty("species_id").GetInt32() == 807, "all 32 boxes/new species");
            Check(boxes[7].GetProperty("slots")[0].GetProperty("form").GetInt32() == 2
                && boxes[0].GetProperty("slots")[0].GetProperty("form").GetInt32() == 1, "Dusk Lycanroc/Own Tempo Rockruff forms");
            Check(obs.GetProperty("progress").ValueKind == JsonValueKind.Null, "unknown progress");
            Check(Read(bytes).GetRawText() == result.GetRawText() && hash.SequenceEqual(SHA256.HashData(bytes)), "deterministic/immutable original");
            var folder = Path.Combine(output, "usum", game.ToString());
            Directory.CreateDirectory(folder);
            File.WriteAllBytes(Path.Combine(folder, "main"), bytes);
            save.Money = 77;
            File.WriteAllBytes(Path.Combine(folder, "later"), save.Write());
            foreach (var offset in new[] { save.GetBoxOffset(0), 0x6C100, bytes.Length - 0x200 + 0x145 })
            {
                var damaged = (byte[])bytes.Clone(); damaged[offset] ^= 0x80;
                Check(Error(damaged) == "CORRUPT_SAVE", "checksum/signature/table rejection " + offset);
            }
            Check(Error(bytes[..^1]) is not null && Error(bytes[..100]) == "TRUNCATED_SAVE", "truncation rejection");
            var badMon = new SAV7USUM((byte[])bytes.Clone());
            badMon.Data[badMon.GetBoxOffset(0) + 10] ^= 0x80;
            Check(Error(badMon.Write()) == "CORRUPT_SAVE", "inner checksum rejection");
            save.Version = GameVersion.SN;
            Check(Error(save.Write()) == "UNSUPPORTED_VERSION", "SM ID in USUM layout rejected");
            save.Version = game;
            foreach (var bad in new[] { "species", "form", "move", "item", "ability" })
            {
                var mon = Pokemon(123);
                switch (bad)
                {
                    case "species": mon.Species = 808; break;
                    case "form": mon.Form = 255; break;
                    case "move": mon.Move1 = 729; break;
                    case "item": mon.HeldItem = 960; break;
                    case "ability": mon.Ability = 234; break;
                }
                save.PartyData = new PKM[] { mon };
                Check(Error(save.Write()) == "CORRUPT_SAVE", "native limit " + bad);
            }
        }
    }
}
