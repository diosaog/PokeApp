using PKHeX.Core;
using System.Text.Json;
using System.Security.Cryptography;

namespace PokeApp.Parser;

// Only this assembly knows PKHeX. No SaveFile/PKM escapes this byte -> JSON boundary.
public static class Inspection
{
    public const int MaxBytes = 8 * 1024 * 1024;
    public const string ParserVersion = "pokeapp-reader/3;pkhex/24.11.11";
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
            var save = SaveUtil.GetVariantSAV((byte[])bytes.Clone());
            if (save is null) return Failure("CORRUPT_SAVE");
            if (save is not (SAV3RS or SAV3E or SAV3FRLG or SAV4DP or SAV4Pt or SAV4HGSS or SAV5BW or SAV5B2W2 or SAV6XY or SAV6AO or SAV7SM))
                return Failure("UNSUPPORTED_GAME");
            if (!save.IsVersionValid()) return Failure("UNSUPPORTED_VERSION");
            if (save is SAV6XY && bytes.Length != SaveUtil.SIZE_G6XY)
                return Failure("UNSUPPORTED_VERSION"); // Decrypted native X/Y only.
            if (save is SAV6AO && bytes.Length != SaveUtil.SIZE_G6ORAS)
                return Failure("UNSUPPORTED_VERSION"); // Decrypted native ORAS, not demo/container.
            // SAV7 clears its signature buffer during construction. Validate the
            // original signature and checksum-table binding, without touching input.
            if (save is SAV7SM)
            {
                if (bytes.Length != SaveUtil.SIZE_G7SM || save.Version is not (GameVersion.SN or GameVersion.MN))
                    return Failure("UNSUPPORTED_VERSION");
                var signature = bytes.AsSpan(0x6BA00 + MemeCrypto.SaveFileSignatureOffset, MemeCrypto.SaveFileSignatureLength);
                if (!MemeCrypto.VerifyMemeData(signature, out var verified, MemeKeyIndex.PokedexAndSaveFile)
                    || !SHA256.HashData(bytes.AsSpan(bytes.Length - 0x200, 0x140)).AsSpan().SequenceEqual(verified.AsSpan(0, 32)))
                    return Failure("CORRUPT_SAVE");
            }
            // This pinned library's Gen5 IsVersionValid inherits an unconditional
            // true. Reject absent or mismatched trainer game IDs explicitly.
            if (save is SAV5BW && save.Version is not (GameVersion.B or GameVersion.W)
                || save is SAV5B2W2 && save.Version is not (GameVersion.B2 or GameVersion.W2))
                return Failure("UNSUPPORTED_VERSION");
            if (!save.ChecksumsValid || save.PartyCount is < 0 or > 6)
                return Failure("CORRUPT_SAVE");
            if (save.BoxSlotCount != 30 || save.BoxCount < 1 || save.BoxCount > (save is SAV7SM ? 32 : save is SAV6 ? 31 : 24))
                return Failure("UNSUPPORTED_VERSION");
            var party = save.PartyData;
            var boxes = save.BoxData;
            var observation = new
            {
                Game = save.Version.ToString(),
                Generation = save.Generation,
                Trainer = new { Name = save.OT, Tid = save.TID16, Sid = save.SID16,
                    Gender = save.Gender, Language = save.Language < 0 ? (int?)null : save.Language },
                // Gen6/7 read support does not claim an approved progress mapping.
                Progress = save.Generation >= 6 ? null : Progress(save),
                Party = Enumerable.Range(0, 6).Select(i => i < party.Count ? Pokemon(party[i], save) : null).ToArray(),
                Boxes = Enumerable.Range(0, save.BoxCount).Select(b => new
                {
                    Number = b + 1,
                    Slots = Enumerable.Range(0, 30).Select(s => Pokemon(boxes[b * 30 + s], save)).ToArray(),
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

    private static object BadgeRegion(string region, int flags) => new
    {
        Region = region,
        BadgeFlags = Enumerable.Range(0, 8).Select(bit => (flags & (1 << bit)) != 0).ToArray(),
    };

    private static object Progress(SaveFile save)
    {
        // Read the pinned library's badge flags, never infer them from a count,
        // playtime, party strength or another region's badges. HGSS's Badges16
        // property is its separate second-region byte, not a sixteen-bit mask.
        (string primary, object[] regions) = save switch
        {
            SAV3FRLG s => ("kanto", new[] { BadgeRegion("kanto", s.Badges) }),
            SAV3 s => ("hoenn", new[] { BadgeRegion("hoenn", s.Badges) }),
            SAV4HGSS s => ("johto", new[] { BadgeRegion("johto", s.Badges), BadgeRegion("kanto", s.Badges16) }),
            SAV4 s => ("sinnoh", new[] { BadgeRegion("sinnoh", s.Badges) }),
            SAV5 s => ("unova", new[] { BadgeRegion("unova", s.Misc.Badges) }),
            _ => throw new InvalidOperationException(),
        };
        // Native event flags documented by this pinned PKHeX release. BW's
        // game-clear flag means Ghetsis, NOT Alder: require its Hall-of-Fame
        // registration instead. Main-block checksums were validated above.
        bool? champion = save switch
        {
            SAV3RS s => s.GetEventFlag(0x804),
            SAV3E s => s.GetEventFlag(2148),
            SAV3FRLG s => s.GetEventFlag(2092),
            SAV4 s => s.GetEventFlag(2404),
            SAV5B2W2 s => s.EventWork.GetEventFlag(2400),
            SAV5BW s => s.PlayerData.IsMagicHallOfFame && s.PlayerData.CountHallOfFame is > 0 and < uint.MaxValue
                ? true : !s.PlayerData.IsMagicHallOfFame && s.PlayerData.CountHallOfFame == 0 ? false : null,
            _ => null,
        };
        return new { SchemaVersion = 1, PrimaryRegion = primary, Regions = regions, ChampionDefeated = champion };
    }

    private static object? Pokemon(PKM p, SaveFile save)
    {
        if (p.Species == 0) return null;
        if (!p.ChecksumValid || p.Species > p.MaxSpeciesID || p.Format is < 3 or > 7)
            throw new InvalidPokemonException();
        if (p.Format != save.Generation || (save.Generation >= 6 &&
            new[] { p.Move1, p.Move2, p.Move3, p.Move4 }.Any(move => move > save.MaxMoveID)))
            throw new InvalidPokemonException();
        if (string.IsNullOrWhiteSpace(p.OriginalTrainerName) || (int)p.Version == 0 || p.Language == 0)
            throw new IncompleteIdentityException();
        var value = new
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
                EncryptionConstant = p.Format >= 6 ? p.EncryptionConstant : (uint?)null,
                Ivs = new[] { p.IV_HP, p.IV_ATK, p.IV_DEF, p.IV_SPA, p.IV_SPD, p.IV_SPE },
            },
        };
        if (save is SAV6AO or SAV7SM)
        {
            if (!save.Personal.IsPresentInGame(p.Species, p.Form))
                throw new InvalidPokemonException();
            var personal = save.Personal.GetFormEntry(p.Species, p.Form);
            // Additive ORAS/SM evidence keeps the existing X/Y/Gen3-5 wire
            // representation and replay digests byte-for-byte compatible.
            var node = JsonSerializer.SerializeToNode(value, Json)!;
            node["type_ids"] = JsonSerializer.SerializeToNode(new[] { (int)personal.Type1, (int)personal.Type2 });
            return node;
        }
        return value;
    }

    private sealed class InvalidPokemonException : Exception;
    private sealed class IncompleteIdentityException : Exception;
}
