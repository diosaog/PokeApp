using PKHeX.Core;
using PokeApp.Parser;
using System.Security.Cryptography;
using System.Text.Json;
using static System.Buffers.Binary.BinaryPrimitives;

// Synthetic native-format fixtures ONLY. Never evidence of authentic gameplay.
internal static class ORASChecks
{
    private static void Check(bool ok, string label)
    {
        if (!ok) throw new Exception(label);
        Console.WriteLine("PASS ORAS synthetic " + label);
    }
    private static JsonElement Read(byte[] bytes) => JsonSerializer.SerializeToElement(Inspection.Inspect(bytes), Inspection.Json);
    private static string? Error(byte[] bytes) => Read(bytes).GetProperty("error").GetString();
    public static void Run(string output)
    {
        foreach (var game in new[] { GameVersion.OR, GameVersion.AS })
        {
            var save = new SAV6AO { Version = game, OT = "ORAS Fixture", TID16 = 5678, SID16 = 1234, Language = 7, Gender = 1 };
            WriteUInt32LittleEndian(save.Data.AsSpan(save.Data.Length - 0x1F0), SaveUtil.BEEF);
            PK6 Pokemon(uint id, ushort species = 479, byte form = 1) => new()
            {
                Species = species, Form = form, PID = id, EncryptionConstant = id + 1000,
                OriginalTrainerName = "ORAS Fixture", TID16 = 5678, SID16 = 1234,
                Language = 7, Version = game, CurrentLevel = 42, Nickname = "Compañero",
                HeldItem = 752, Move1 = 621, Move1_PP = 5, Ability = 26, Nature = Nature.Timid,
                IV_HP = 31, IV_SPE = 29, EV_SPE = 252, MetLevel = 5, MetLocation = 10,
            };
            save.PartyData = new PKM[] { Pokemon(123) };
            save.SetBoxSlotAtIndex(Pokemon(456, 25, 3), 0, 0); // ORAS cosplay form.
            save.SetBoxSlotAtIndex(Pokemon(789), 7, 0);
            save.SetBoxSlotAtIndex(Pokemon(987, 386, 2), 30, 29);
            var bytes = save.Write();
            var hash = SHA256.HashData(bytes);
            var result = Read(bytes);
            Check(result.GetProperty("error").ValueKind == JsonValueKind.Null, game + " parsed");
            var obs = result.GetProperty("observation");
            Check(obs.GetProperty("game").GetString() == game.ToString(), "content game identity");
            Check(obs.GetProperty("trainer").GetProperty("tid").GetInt32() == 5678, "trainer mapping");
            var party = obs.GetProperty("party");
            Check(party.GetArrayLength() == 6 && party[1].ValueKind == JsonValueKind.Null, "party/empty slots");
            Check(party[0].GetProperty("form").GetInt32() == 1
                && party[0].GetProperty("type_ids")[0].GetInt32() == 12
                && party[0].GetProperty("type_ids")[1].GetInt32() == 9, "Rotom Heat form/types");
            Check(party[0].GetProperty("moves")[0].GetProperty("id").GetInt32() == 621
                && party[0].GetProperty("item_id").GetInt32() == 752, "ORAS move/item range");
            var boxes = obs.GetProperty("boxes");
            Check(boxes.GetArrayLength() == 31 && boxes[30].GetProperty("slots")[29].GetProperty("form").GetInt32() == 2
                && boxes[7].GetProperty("slots")[0].ValueKind == JsonValueKind.Object, "last box/form/dead slot");
            Check(obs.GetProperty("progress").ValueKind == JsonValueKind.Null, "no fabricated progress");
            Check(Read(bytes).GetRawText() == result.GetRawText() && hash.SequenceEqual(SHA256.HashData(bytes)), "determinism/input unchanged");
            var folder = Path.Combine(output, "oras", game.ToString());
            Directory.CreateDirectory(folder);
            File.WriteAllBytes(Path.Combine(folder, "main"), bytes);
            save.Money = 77;
            File.WriteAllBytes(Path.Combine(folder, "later"), save.Write());
            var damaged = (byte[])bytes.Clone(); damaged[0x33000] ^= 0x80;
            Check(Error(damaged) == "CORRUPT_SAVE", "PC checksum rejection");
            Check(Error(bytes[..^1]) is not null && Error(bytes[..100]) == "TRUNCATED_SAVE", "truncation rejection");
            var badMon = new SAV6AO((byte[])bytes.Clone());
            badMon.Data[badMon.GetBoxOffset(0) + 10] ^= 0x80;
            Check(Error(badMon.Write()) == "CORRUPT_SAVE", "inner checksum rejection");
            save.Version = GameVersion.X;
            Check(Error(save.Write()) == "UNSUPPORTED_VERSION", "XY ID in ORAS layout rejected");
            save.Version = game;
            save.PartyData = new PKM[] { Pokemon(123, 25, 255) };
            Check(Error(save.Write()) == "CORRUPT_SAVE", "invalid form rejection");
        }
        Check(new SAV6AO().MaxMoveID == 621, "pinned ORAS move ceiling");
    }
}
