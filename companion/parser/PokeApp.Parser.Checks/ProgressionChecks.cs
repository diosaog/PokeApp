using PKHeX.Core;
using PokeApp.Parser;
using System.Security.Cryptography;
using System.Text.Json;
using static System.Buffers.Binary.BinaryPrimitives;

// Synthetic native-format interpretation cases, not gameplay transition proof.
// Writes are limited to newly created disposable fixtures; Inspection gets bytes.
internal static class ProgressionChecks
{
    private static void Check(bool condition, string label)
    {
        if (!condition) throw new Exception(label);
        Console.WriteLine("PASS progression " + label);
    }

    private static JsonElement Read(byte[] bytes)
        => JsonSerializer.SerializeToElement(Inspection.Inspect(bytes), Inspection.Json);

    private static JsonElement Observe(SaveFile save, string label)
    {
        var bytes = save.Write();
        var before = SHA256.HashData(bytes);
        var result = Read(bytes);
        Check(result.GetProperty("error").ValueKind == JsonValueKind.Null, label + " native integrity accepted");
        Check(before.SequenceEqual(SHA256.HashData(bytes)) && result.GetRawText() == Read(bytes).GetRawText(), label + " input bytes unchanged and deterministic");
        var observation = result.GetProperty("observation");
        Check(observation.GetProperty("progress").ValueKind == JsonValueKind.Null, label + " automatic reward projection disabled");
        var native = observation.GetProperty("native_progress");
        Check(native.GetProperty("schema_version").GetInt32() == 1
            && native.GetProperty("league_access").ValueKind == JsonValueKind.Null, label + " League eligibility remains unknown");
        return native;
    }

    public static void Run(string output)
    {
        foreach (var game in new[] { GameVersion.X, GameVersion.Y, GameVersion.OR, GameVersion.AS, GameVersion.SN, GameVersion.MN, GameVersion.US, GameVersion.UM })
        {
            SaveFile save = game switch
            {
                GameVersion.X or GameVersion.Y => new SAV6XY(),
                GameVersion.OR or GameVersion.AS => new SAV6AO(),
                GameVersion.SN or GameVersion.MN => new SAV7SM(),
                _ => new SAV7USUM(),
            };
            save.Version = game;
            save.OT = "Progress test";
            save.TID16 = 12345;
            save.SID16 = 54321;
            save.Language = 2;
            WriteUInt32LittleEndian(save.Data.AsSpan(save.Data.Length - 0x1F0), SaveUtil.BEEF);

            var zero = Observe(save, game + " zero");
            if (save is SAV6 six)
            {
                Check(zero.GetProperty("model").GetString() == "gym_badges"
                    && zero.GetProperty("badge_flags").GetArrayLength() == 8
                    && zero.GetProperty("badge_flags").EnumerateArray().All(f => !f.GetBoolean())
                    && zero.GetProperty("island_stamp_flags").ValueKind == JsonValueKind.Null
                    && zero.GetProperty("island_challenge_completed").ValueKind == JsonValueKind.Null,
                    game + " exact zero badges; no island progress");
                foreach (var mask in new[] { 0b10100101, 0xff })
                {
                    six.Badges = mask;
                    var progress = Observe(save, game + " badge mask " + mask);
                    Check(progress.GetProperty("badge_flags").EnumerateArray().Select(f => f.GetBoolean())
                        .SequenceEqual(Enumerable.Range(0, 8).Select(bit => (mask & (1 << bit)) != 0)), game + " exact sparse/full badges");
                    Check(!progress.GetProperty("hall_of_fame_entered").GetBoolean()
                        && !progress.GetProperty("champion_defeated").GetBoolean(),
                        game + " eight badges cannot invent Champion or Hall of Fame");
                }
                six.EventWork.SetEventFlag(game is GameVersion.X or GameVersion.Y ? 2735 : 2901, true);
                if (six is SAV6AO) six.EventWork.SetEventFlag(2897, true);
                var league = Observe(save, game + " League destination");
                Check(league.GetProperty("league_fly_unlocked").GetBoolean()
                    && !league.GetProperty("champion_defeated").GetBoolean()
                    && !league.GetProperty("hall_of_fame_entered").GetBoolean(), game + " League destination independent of completion");
                Check(six is SAV6AO ? league.GetProperty("league_visited").GetBoolean()
                    : league.GetProperty("league_visited").ValueKind == JsonValueKind.Null, game + " only documented League visited field");
                six.EventWork.SetEventFlag(game is GameVersion.X or GameVersion.Y ? 2640 : 2720, true);
                var fame = Observe(save, game + " HoF flag");
                Check(fame.GetProperty("hall_of_fame_entered").GetBoolean()
                    && fame.GetProperty("champion_defeated").ValueKind == JsonValueKind.Null, game + " uncorroborated HoF flag is not Champion proof");
                var hall = six is SAV6XY xy ? xy.HallOfFame : ((SAV6AO)six).HallOfFame;
                var index = new HallFame6Index(hall.GetEntry(0)[^HallFame6Index.SIZE..]);
                index.HasData = true; index.ClearIndex = 0; index.Year = 24; index.Month = 7; index.Day = 8;
                var member = new HallFame6Entity(hall.GetEntity(0, 0), save.Language);
                member.Species = 25;
                Check(Observe(save, game + " corroborated first clear").GetProperty("champion_defeated").GetBoolean(),
                    game + " independent native first-clear record proves observed completion");
                six.EventWork.SetEventFlag(game is GameVersion.X or GameVersion.Y ? 2640 : 2720, false);
                Check(Observe(save, game + " absent HoF flag").GetProperty("champion_defeated").ValueKind == JsonValueKind.Null,
                    game + " first-clear record without corroborating flag is unknown");
                six.EventWork.SetEventFlag(game is GameVersion.X or GameVersion.Y ? 2640 : 2720, true);
                index.Month = 13;
                Check(Observe(save, game + " malformed clear date").GetProperty("champion_defeated").ValueKind == JsonValueKind.Null,
                    game + " malformed completion record is unknown");
                index.Month = 7; index.ClearIndex = 1;
                Check(Observe(save, game + " non-first clear index").GetProperty("champion_defeated").ValueKind == JsonValueKind.Null,
                    game + " malformed first-clear index is unknown");
                index.ClearIndex = 0; member.Species = (ushort)(save.MaxSpeciesID + 1);
                Check(Observe(save, game + " invalid recorded species").GetProperty("champion_defeated").ValueKind == JsonValueKind.Null,
                    game + " invalid Hall record species is unknown");
                member.Species = 0;
                Check(Observe(save, game + " empty first-clear team").GetProperty("champion_defeated").ValueKind == JsonValueKind.Null,
                    game + " empty first-clear team is unknown");
                member.Species = 25;
                six.Badges = 0;
                var contradictory = Observe(save, game + " contradictory badge state");
                Check(contradictory.GetProperty("badge_flags").EnumerateArray().All(f => !f.GetBoolean())
                    && contradictory.GetProperty("champion_defeated").GetBoolean(),
                    game + " observed contradictions do not manufacture badges");
            }
            else if (save is SAV7 seven)
            {
                Check(zero.GetProperty("model").GetString() == "island_challenge"
                    && zero.GetProperty("badge_flags").ValueKind == JsonValueKind.Null
                    && zero.GetProperty("hall_of_fame_entered").ValueKind == JsonValueKind.Null
                    && zero.GetProperty("league_visited").ValueKind == JsonValueKind.Null
                    && zero.GetProperty("league_fly_unlocked").ValueKind == JsonValueKind.Null,
                    game + " no fabricated badges or unsupported League facts");
                seven.Misc.Stamps = (1u << 0) | (1u << 1) | (1u << 3) | (1u << 6);
                var sparse = Observe(save, game + " sparse island stamps");
                Check(sparse.GetProperty("island_stamp_flags").EnumerateArray().Select(f => f.GetBoolean())
                    .SequenceEqual(new[] { true, false, true, false })
                    && !sparse.GetProperty("island_challenge_completed").GetBoolean()
                    && !sparse.GetProperty("champion_defeated").GetBoolean(), game + " unrelated stamps excluded; islands do not invent completion");
                seven.Misc.Stamps = 0x7fff;
                var all = Observe(save, game + " all stamps");
                Check(all.GetProperty("island_stamp_flags").EnumerateArray().All(f => f.GetBoolean())
                    && all.GetProperty("island_challenge_completed").GetBoolean()
                    && !all.GetProperty("champion_defeated").GetBoolean(), game + " island challenge stamp does not invent Champion");
                seven.EventWork.SetEventFlag(seven is SAV7SM ? 3100 : 4060, true);
                seven.Misc.Stamps = 0;
                var champion = Observe(save, game + " Champion event");
                Check(champion.GetProperty("champion_defeated").GetBoolean()
                    && !champion.GetProperty("island_challenge_completed").GetBoolean()
                    && champion.GetProperty("island_stamp_flags").EnumerateArray().All(f => !f.GetBoolean()),
                    game + " title-specific Champion event independent of stamp observations");
                // A similarly numbered flag from the other family cannot be used.
                seven.EventWork.SetEventFlag(seven is SAV7SM ? 3100 : 4060, false);
                if (seven is SAV7USUM) seven.EventWork.SetEventFlag(3100, true);
                Check(!Observe(save, game + " different family flag").GetProperty("champion_defeated").GetBoolean(), game + " exact family mapping");
            }
            var finalBytes = save.Write();
            File.WriteAllBytes(Path.Combine(output, game + "-progress.main"), finalBytes);
            var corrupt = (byte[])finalBytes.Clone();
            corrupt[0x100] ^= 0x80;
            Check(Read(corrupt).GetProperty("error").GetString() == "CORRUPT_SAVE", game + " bad checksums cannot expose progress");
        }
        Console.WriteLine("RESULT OK; eight-game synthetic native progression checks");
    }
}
