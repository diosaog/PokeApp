using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;

// Docker-only fixtures built from the existing blank-save checks. No user save
// is read. The final Python image must exercise its actual portable writer.
internal static class ChecksRuntimeSmoke
{
    private static int[] Ivs(PKM p) => [p.IV_HP, p.IV_ATK, p.IV_DEF, p.IV_SPA, p.IV_SPD, p.IV_SPE];

    public static void Export(string fixtureRoot, string outputRoot)
    {
        Directory.CreateDirectory(outputRoot);
        var cases = new List<object>();
        foreach (var (game, family) in new[] { ("X", "xy"), ("Y", "xy"), ("OR", "oras"), ("AS", "oras"),
                     ("SN", "sm"), ("MN", "sm"), ("US", "usum"), ("UM", "usum") })
        {
            var original = File.ReadAllBytes(Path.Combine(fixtureRoot, family, game, "main"));
            byte[] source = [];
            // PKHeX can emit a short RSA result in its fixed signature buffer.
            // Vary only this synthetic PKM's EC; accept no invalid signature,
            // disabled checksum check, or normalization of an external save.
            for (uint nonce = 0; nonce < 1024; nonce++)
            {
                var save = SaveUtil.GetVariantSAV((byte[])original.Clone())
                    ?? throw new Exception(game + " synthetic base save unavailable");
                var pokemon = TrainingChecks.Specimen(save);
                pokemon.EncryptionConstant += nonce;
                save.PartyData = [pokemon.Clone()];
                TrainingChecks.Put(save, pokemon.Clone(), "party");
                TrainingChecks.Put(save, pokemon.Clone(), "box");
                var candidate = save.Write().ToArray();
                if (save.Generation == 7 && !NativeSignature.VerifySave(candidate)) continue;
                var inspected = JsonSerializer.SerializeToElement(Inspection.Inspect(candidate), Inspection.Json);
                if (inspected.GetProperty("error").ValueKind != JsonValueKind.Null
                    || inspected.GetProperty("observation").GetProperty("game").GetString() != game)
                    throw new Exception(game + " synthetic training source failed native inspection");
                source = candidate;
                break;
            }
            if (source.Length == 0) throw new Exception(game + " could not generate a signed synthetic source");
            var folder = Path.Combine(outputRoot, game);
            Directory.CreateDirectory(folder);
            File.WriteAllBytes(Path.Combine(folder, "main"), source);
            foreach (var (item, location) in new[] { ("menta_naturaleza", "party"),
                         ("chapa_plateada", "box"), ("chapa_dorada", "party") })
            {
                var request = TrainingChecks.Request(source, location, item,
                    nature: item == "menta_naturaleza" ? (int)Nature.Modest : null,
                    stat: item == "chapa_plateada" ? "hp" : null);
                var save = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
                var before = location == "party" ? save.GetPartySlotAtIndex(0) : save.GetBoxSlotAtIndex(0, 0);
                if (before is IHyperTrain flags && flags.HyperTrainFlags != 0)
                    throw new Exception(game + " synthetic source has Hyper Training flags");
                var after = before.Clone();
                if (item == "menta_naturaleza") after.Nature = Nature.Modest;
                else
                {
                    after.IV_HP = 31;
                    if (item == "chapa_dorada")
                        after.IV_ATK = after.IV_DEF = after.IV_SPA = after.IV_SPD = after.IV_SPE = 31;
                }
                after.RefreshChecksum();
                if (after is IHyperTrain afterFlags && afterFlags.HyperTrainFlags != 0)
                    throw new Exception(game + " expected PKM has Hyper Training flags");
                cases.Add(new
                {
                    game, item_code = item, source_file = game + "/main", intent = request["intent"]!.DeepClone(),
                    expected = new
                    {
                        nature = (int)after.Nature, ivs = Ivs(after),
                        pokemon_sha256 = NativeWrite.Hash(after.DecryptedBoxData),
                        // Hash includes all 232 stored bytes, including Gen7's
                        // unchanged Hyper Training flags; party stats are
                        // independently checked by the native output verifier.
                        no_hyper_training = true,
                    },
                });
            }
        }
        if (cases.Count != 24) throw new Exception("training runtime case count");
        File.WriteAllText(Path.Combine(outputRoot, "cases.json"), JsonSerializer.Serialize(
            new { schema_version = 1, cases }, Inspection.Json));
        Console.WriteLine("PASS generated 24 synthetic training runtime cases across all eight games");
    }
}
