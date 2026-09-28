using PKHeX.Core;
using System.Text.Json;

namespace PokeApp.Parser;

// Only this assembly knows PKHeX. No SaveFile/PKM escapes this byte -> JSON boundary.
public static class Inspection
{
    public const int MaxBytes = 8 * 1024 * 1024;
    public const string ParserVersion = "pokeapp-reader/1;pkhex/24.11.11";
    public static readonly JsonSerializerOptions Json = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    public static object Inspect(byte[] bytes)
    {
        if (bytes.Length < 0x10000) return Failure("TRUNCATED_SAVE");
        if (bytes.Length > MaxBytes) return Failure("UNSUPPORTED_VERSION");
        try
        {
            var save = SaveUtil.GetVariantSAV(bytes);
            if (save is null) return Failure("CORRUPT_SAVE");
            if (save is not (SAV3RS or SAV3E or SAV3FRLG or SAV4DP or SAV4Pt or SAV4HGSS or SAV5BW or SAV5B2W2))
                return Failure("UNSUPPORTED_GAME");
            if (!save.IsVersionValid()) return Failure("UNSUPPORTED_VERSION");
            if (!save.ChecksumsValid || save.PartyCount is < 0 or > 6)
                return Failure("CORRUPT_SAVE");
            if (save.BoxSlotCount != 30 || save.BoxCount is < 1 or > 24)
                return Failure("UNSUPPORTED_VERSION");
            var party = save.PartyData;
            var boxes = save.BoxData;
            var observation = new
            {
                Game = save.Version.ToString(),
                Generation = save.Generation,
                Trainer = new { Name = save.OT, Tid = save.TID16, Sid = save.SID16,
                    Gender = save.Gender, Language = save.Language < 0 ? (int?)null : save.Language },
                Party = Enumerable.Range(0, 6).Select(i => i < party.Count ? Pokemon(party[i]) : null).ToArray(),
                Boxes = Enumerable.Range(0, save.BoxCount).Select(b => new
                {
                    Number = b + 1,
                    Slots = Enumerable.Range(0, 30).Select(s => Pokemon(boxes[b * 30 + s])).ToArray(),
                }).ToArray(),
            };
            return new { SchemaVersion = 1, ParserVersion, Observation = observation, Error = (string?)null };
        }
        catch (InvalidPokemonException) { return Failure("CORRUPT_SAVE"); }
        catch (IncompleteIdentityException) { return Failure("AMBIGUOUS_IDENTITY"); }
        catch (Exception) { return Failure("PARSER_FAILURE"); } // Never expose dependency errors or a fake empty save.
    }

    public static object Failure(string code) => new
        { SchemaVersion = 1, ParserVersion, Observation = (object?)null, Error = code };

    private static object? Pokemon(PKM p)
    {
        if (p.Species == 0) return null;
        if (!p.ChecksumValid || p.Species > p.MaxSpeciesID || p.Format is < 3 or > 5)
            throw new InvalidPokemonException();
        if (string.IsNullOrWhiteSpace(p.OriginalTrainerName) || (int)p.Version == 0 || p.Language == 0)
            throw new IncompleteIdentityException();
        return new
        {
            SpeciesId = p.Species, p.Nickname, Level = p.CurrentLevel, p.Form, p.Gender,
            Shiny = p.IsShiny, p.IsEgg, AbilityId = p.Ability, NatureId = (int)p.Nature,
            ItemId = p.HeldItem,
            Moves = new[] { new { Id = p.Move1, Pp = p.Move1_PP }, new { Id = p.Move2, Pp = p.Move2_PP },
                new { Id = p.Move3, Pp = p.Move3_PP }, new { Id = p.Move4, Pp = p.Move4_PP } },
            Ivs = new[] { p.IV_HP, p.IV_ATK, p.IV_DEF, p.IV_SPA, p.IV_SPD, p.IV_SPE },
            Evs = new[] { p.EV_HP, p.EV_ATK, p.EV_DEF, p.EV_SPA, p.EV_SPD, p.EV_SPE },
            Identity = new
            {
                SchemaVersion = 1, p.Format, Pid = p.PID, OtTid = p.TID16, OtSid = p.SID16,
                OriginVersion = (int)p.Version, p.Language, OtName = p.OriginalTrainerName,
                OtGender = p.OriginalTrainerGender, p.MetLocation, p.MetLevel,
                EggLocation = p.Format == 3 ? (int?)null : p.EggLocation,
                MetDate = p.MetDate?.ToString("yyyy-MM-dd"), EggDate = p.EggMetDate?.ToString("yyyy-MM-dd"),
                EncryptionConstant = (uint?)null,
                Ivs = new[] { p.IV_HP, p.IV_ATK, p.IV_DEF, p.IV_SPA, p.IV_SPD, p.IV_SPE },
            },
        };
    }

    private sealed class InvalidPokemonException : Exception;
    private sealed class IncompleteIdentityException : Exception;
}
