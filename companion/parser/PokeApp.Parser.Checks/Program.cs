using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;
using static System.Buffers.Binary.BinaryPrimitives;

// Fixtures are generated here from blank save/PKM objects. No personal/third-party saves.
static void Check(bool condition, string name)
{
    if (!condition) throw new Exception(name);
    Console.WriteLine("PASS " + name);
}
static JsonElement Read(byte[] bytes) => JsonSerializer.SerializeToElement(Inspection.Inspect(bytes), Inspection.Json);
static SAV3E Emerald()
{
    var bytes = new byte[0x20000];
    for (int group = 0; group < 2; group++)
        for (int sector = 0; sector < 14; sector++)
        {
            int offset = group * 0xE000 + sector * 0x1000;
            WriteUInt16LittleEndian(bytes.AsSpan(offset + 0xFF4), (ushort)sector);
            WriteUInt32LittleEndian(bytes.AsSpan(offset + 0xFF8), 0x08012025);
        }
    var save = new SAV3E(bytes) { SecurityKey = 42 };
    save.Small[0x900] = 1; // Emerald data beyond the Ruby/Sapphire small block.
    return save;
}
static SAV4DP DiamondPearl()
{
    var bytes = new byte[0x80000];
    foreach (int offset in new[] { 0, 0x40000 })
    {
        WriteUInt32LittleEndian(bytes.AsSpan(offset + SAV4DP.GeneralSize - 12), SAV4DP.GeneralSize);
        WriteUInt32LittleEndian(bytes.AsSpan(offset + SAV4DP.GeneralSize - 8), SAV4.MAGIC_JAPAN_INTL);
    }
    return new SAV4DP(bytes);
}
static byte[] Fixture(SaveFile save)
{
    save.OT = "Fixture"; save.TID16 = 123; save.SID16 = 456; save.Language = 2;
    PKM p = save.BlankPKM;
    p.Species = 25; p.PID = 123456; p.TID16 = 123; p.SID16 = 456;
    p.OriginalTrainerName = "Fixture"; p.Language = 2;
    p.Version = save.Generation == 3 ? GameVersion.E : save.Generation == 4 ? GameVersion.D : GameVersion.B2;
    p.CurrentLevel = 20; p.Nickname = "Sparky"; p.Move1 = 85; p.Move1_PP = 15;
    p.IV_HP = 20; p.RefreshChecksum();
    save.PartyData = new[] { p };
    var other = p.Clone(); other.PID = 654321; other.RefreshChecksum();
    save.SetBoxSlotAtIndex(other, 0, 0);
    return save.Write();
}
var output = args.Length == 1 ? Path.GetFullPath(args[0]) : null;
if (output is not null) Directory.CreateDirectory(output);
foreach (var save in new SaveFile[] { Emerald(), DiamondPearl(), new SAV5B2W2() })
{
    var bytes = Fixture(save);
    var result = Read(bytes);
    if (result.GetProperty("error").ValueKind != JsonValueKind.Null)
        throw new Exception($"gen{save.Generation}: {result}");
    var observation = result.GetProperty("observation");
    Check(observation.GetProperty("generation").GetInt32() == save.Generation, $"Gen{save.Generation} real binary inspection");
    var party = observation.GetProperty("party");
    Check(party.GetArrayLength() == 6 && party[1].ValueKind == JsonValueKind.Null, "party preserves empty slots");
    Check(party[0].GetProperty("identity").GetProperty("pid").GetUInt32() == 123456, "023 evidence exported");
    Check(party[0].GetProperty("identity").GetProperty("encryption_constant").ValueKind == JsonValueKind.Null, "no invented EC identity");
    var boxes = observation.GetProperty("boxes");
    Check(boxes.GetArrayLength() == save.BoxCount && boxes[0].GetProperty("slots").GetArrayLength() == 30, "full boxes preserved");
    Check(boxes[0].GetProperty("slots")[0].GetProperty("identity").GetProperty("pid").GetUInt32() == 654321, "box Pokemon exported");
    if (output is not null) File.WriteAllBytes(Path.Combine(output, $"gen{save.Generation}.sav"), bytes);
    // Corrupt a byte in the trainer block without regenerating checksums.
    var broken = (byte[])bytes.Clone(); broken[0x100] ^= 0x80;
    Check(Read(broken).GetProperty("error").ValueKind == JsonValueKind.String, "corruption is not an empty success");
}
Check(Read(new byte[20]).GetProperty("error").GetString() == "TRUNCATED_SAVE", "truncation explicit");
Check(Read(new byte[0x80000]).GetProperty("error").GetString() == "CORRUPT_SAVE", "unknown binary rejected");
var unsupported = new byte[SaveUtil.SIZE_G6XY];
WriteUInt32LittleEndian(unsupported.AsSpan(unsupported.Length - 0x1F0), SaveUtil.BEEF);
Check(Read(unsupported).GetProperty("error").GetString() == "UNSUPPORTED_GAME", "unsupported recognized game");
Console.WriteLine("RESULT OK; generated Gen3/4/5 parser checks");
