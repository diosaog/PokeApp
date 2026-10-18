using PKHeX.Core;
using PokeApp.Parser;
using System.Security.Cryptography;
using System.Text.Json;
using static System.Buffers.Binary.BinaryPrimitives;

// Writes below create disposable synthetic fixtures only. The parser has no
// serialization/file-write interface and never receives the source path.
internal static class XYChecks
{
    private static void Check(bool ok, string label)
    {
        if (!ok) throw new Exception(label);
        Console.WriteLine("PASS XY " + label);
    }
    private static JsonElement Read(byte[] bytes) => JsonSerializer.SerializeToElement(Inspection.Inspect(bytes), Inspection.Json);
    private static string? Error(byte[] bytes) => Read(bytes).GetProperty("error").GetString();
    private static SAV6XY Fixture(GameVersion version)
    {
        var save = new SAV6XY { Version = version, OT = "XY Fixture", TID16 = 54321, SID16 = 12345, Language = 7, Gender = 1 };
        WriteUInt32LittleEndian(save.Data.AsSpan(save.Data.Length - 0x1F0), SaveUtil.BEEF);
        PK6 Pokemon(int slot) => new()
        {
            Species = (ushort)(650 + slot), PID = (uint)(123456 + slot), EncryptionConstant = (uint)(987654 + slot),
            TID16 = 54321, SID16 = 12345, OriginalTrainerName = "XY Fixture", OriginalTrainerGender = 1,
            Language = 7, Version = version, CurrentLevel = (byte)(20 + slot), Nickname = "Compañero" + slot,
            HeldItem = 234, Move1 = 560, Move1_PP = 10, Move2 = 85, Move2_PP = 15,
            Ability = 65, Nature = Nature.Timid, IV_HP = 31, IV_ATK = 12, EV_SPE = 252,
            MetLevel = 5, MetLocation = 10,
        };
        save.PartyData = Enumerable.Range(0, 6).Select(i => (PKM)Pokemon(i)).ToArray();
        save.SetBoxSlotAtIndex(Pokemon(6), 0, 0);
        save.SetBoxSlotAtIndex(Pokemon(7), 30, 29);
        return save;
    }
    public static void Run(string? output)
    {
        foreach (var game in new[] { GameVersion.X, GameVersion.Y })
        {
            var save = Fixture(game);
            var bytes = save.Write();
            var hash = SHA256.HashData(bytes);
            var result = Read(bytes);
            Check(result.GetProperty("error").ValueKind == JsonValueKind.Null, game + " native parse " + result.GetProperty("error"));
            var obs = result.GetProperty("observation");
            Check(obs.GetProperty("game").GetString() == game.ToString() && obs.GetProperty("generation").GetInt32() == 6, game + " detected from contents");
            Check(obs.GetProperty("trainer").GetProperty("tid").GetInt32() == 54321
                && obs.GetProperty("trainer").GetProperty("name").GetString() == "XY Fixture", "trainer evidence");
            var party = obs.GetProperty("party");
            Check(party.GetArrayLength() == 6 && party[5].GetProperty("species_id").GetInt32() == 655, "all six party slots");
            Check(party[0].GetProperty("nickname").GetString() == "Compañero0"
                && party[0].GetProperty("level").GetInt32() == 20
                && party[0].GetProperty("item_id").GetInt32() == 234
                && party[0].GetProperty("moves")[0].GetProperty("id").GetInt32() == 560
                && party[0].GetProperty("ivs")[0].GetInt32() == 31
                && party[0].GetProperty("evs")[5].GetInt32() == 252, "neutral Pokemon fields");
            Check(party[0].GetProperty("identity").GetProperty("encryption_constant").GetUInt32() == 987654, "real independent EC");
            var boxes = obs.GetProperty("boxes");
            Check(boxes.GetArrayLength() == 31 && boxes.EnumerateArray().All(b => b.GetProperty("slots").GetArrayLength() == 30), "31 full boxes");
            Check(boxes[0].GetProperty("slots")[0].GetProperty("species_id").GetInt32() == 656
                && boxes[30].GetProperty("number").GetInt32() == 31
                && boxes[30].GetProperty("slots")[29].GetProperty("species_id").GetInt32() == 657
                && boxes[30].GetProperty("slots")[28].ValueKind == JsonValueKind.Null, "first/last exact position and empty slot");
            Check(obs.GetProperty("progress").ValueKind == JsonValueKind.Null, "progress remains unknown");
            Check(Read(bytes).GetRawText() == result.GetRawText() && hash.SequenceEqual(SHA256.HashData(bytes)), "repeated parse stable; input unchanged");
            if (output is not null)
            {
                var folder = Path.Combine(output, "xy", game.ToString());
                Directory.CreateDirectory(folder);
                File.WriteAllBytes(Path.Combine(folder, "main"), bytes);
            }
            var corrupt = (byte[])bytes.Clone(); corrupt[0x14000] ^= 0x80;
            Check(Error(corrupt) == "CORRUPT_SAVE", "trainer block checksum rejected");
            corrupt = (byte[])bytes.Clone(); corrupt[0x22600] ^= 0x80;
            Check(Error(corrupt) == "CORRUPT_SAVE", "PC block checksum rejected");
            var invalidPokemon = new SAV6XY((byte[])bytes.Clone());
            invalidPokemon.Data[invalidPokemon.GetBoxOffset(0) + 10] ^= 0x80;
            Check(Error(invalidPokemon.Write()) == "CORRUPT_SAVE", "bad Pokemon checksum rejected even with valid outer checksums");
            Check(Error(bytes[..^1]) is not null && Error(bytes[..0x1000]) == "TRUNCATED_SAVE", "incomplete input rejected");
            save.Data[save.GetPartyOffset(6)] = 7;
            Check(Error(save.Write()) == "CORRUPT_SAVE", "invalid party count rejected");
            save.Data[save.GetPartyOffset(6)] = 1;
            var sparse = Read(save.Write()).GetProperty("observation").GetProperty("party");
            Check(sparse[0].ValueKind == JsonValueKind.Object && sparse.EnumerateArray().Skip(1).All(p => p.ValueKind == JsonValueKind.Null), "empty party slots preserved");
            save.Version = GameVersion.OR;
            Check(Error(save.Write()) == "UNSUPPORTED_VERSION", "mismatched version in XY layout rejected");
            save.Version = GameVersion.Any;
            Check(Error(save.Write()) == "UNSUPPORTED_VERSION", "missing trainer game rejected");
        }
        foreach (var size in new[] { SaveUtil.SIZE_G7USUM })
        {
            var bytes = new byte[size];
            WriteUInt32LittleEndian(bytes.AsSpan(size - 0x1F0), SaveUtil.BEEF);
            Check(Error(bytes) == "UNSUPPORTED_VERSION", "absent USUM game ID rejected " + size);
        }
        Check(new SAV6XY().MaxMoveID == 617, "XY move ceiling confirmed from pinned library");
    }
}
