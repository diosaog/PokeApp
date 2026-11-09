using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;

// Disposable test saves for the 085 acceptance: three distinct trainers of the
// same game, each owning its Pokémon and with one in Caja 7. Derived from a
// public format fixture; never written anywhere but the given output folder.
internal static class Phase085Fixtures
{
    public static void Run(string manifestPath, string outputDirectory)
    {
        using var manifest = JsonDocument.Parse(File.ReadAllBytes(manifestPath));
        var root = Environment.ExpandEnvironmentVariables(manifest.RootElement.GetProperty("binary_root").GetString()!);
        var original = File.ReadAllBytes(Path.Combine(root, "Y-before-transfer", "main"));
        foreach (var (name, id) in new[] { ("Alfa", (ushort)0x1234), ("Bravo", (ushort)0x2345), ("Carla", (ushort)0x3456) })
        {
            var save = SaveUtil.GetVariantSAV((byte[])original.Clone())!;
            save.OT = name;
            save.TID16 = id;
            save.SID16 = (ushort)(id ^ 0x0F0F);
            uint salt = (uint)(id * 0x10001);
            uint n = 0;
            PKM Mine(PKM p)
            {
                var mon = p.Clone();
                n++;
                mon.TID16 = save.TID16; mon.SID16 = save.SID16;
                mon.OriginalTrainerName = save.OT; mon.OriginalTrainerGender = (byte)save.Gender;
                mon.Language = save.Language; mon.Version = save.Version;
                mon.MetDate = new DateOnly(2020, 1, 1); mon.MetLevel = 10; mon.MetLocation = 1;
                mon.EggLocation = 0; mon.EggMetDate = null; mon.IsEgg = false;
                mon.PID = salt + n * 0x101; mon.EncryptionConstant = ~(salt + n * 0x103);
                mon.RefreshChecksum();
                return mon;
            }
            PKM? sample = null;
            for (int b = 0; b < save.BoxCount; b++)
                for (int s = 0; s < 30; s++)
                {
                    var p = save.GetBoxSlotAtIndex(b, s);
                    if (p.Species == 0) continue;
                    // Ten living Pokémon and free space: the rest is emptied.
                    if (b != 0 || s >= 10)
                    {
                        save.WriteBoxSlot(save.BlankPKM, save.Data.AsSpan(save.GetBoxSlotOffset(b, s), 232));
                        continue;
                    }
                    var mine = Mine(p);
                    sample ??= mine;
                    save.WriteBoxSlot(mine, save.Data.AsSpan(save.GetBoxSlotOffset(b, s), 232));
                }
            for (int s = 0; s < save.PartyCount; s++)
            {
                var mine = Mine(save.GetPartySlotAtIndex(s));
                sample ??= mine;
                save.WritePartySlot(mine, save.Data.AsSpan(save.GetPartyOffset(s), 260));
            }
            // One Pokémon in the official dead box (zero-based index 6).
            save.WriteBoxSlot(Mine(sample!), save.Data.AsSpan(save.GetBoxSlotOffset(6, 0), 232));
            var folder = Path.Combine(outputDirectory, name);
            Directory.CreateDirectory(folder);
            File.WriteAllBytes(Path.Combine(folder, "main"), save.Write());
            Console.WriteLine("FIXTURE " + name);
        }
    }
}
