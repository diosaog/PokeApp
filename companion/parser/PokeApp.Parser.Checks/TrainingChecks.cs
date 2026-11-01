using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Numerics;
using System.Security.Cryptography;

// Derived public-fixture copies and synthetic PKM only. No owner save is opened.
// Checks the real native protocol and independently forged, valid-checksum output.
internal static class TrainingChecks
{
    private static int checks;
    private static void Check(bool value, string label)
    {
        if (!value) throw new Exception(label);
        checks++;
    }
    private static JsonObject Node(object value) => JsonSerializer.SerializeToNode(value, Inspection.Json)!.AsObject();
    private static JsonObject Execute(JsonObject request, bool verify = false)
        => Node(NativeWrite.Execute(JsonSerializer.SerializeToUtf8Bytes(request), verify));
    private static JsonObject Copy(JsonObject request) => request.DeepClone().AsObject();
    private static string? Error(JsonObject response) => response["error"]?.GetValue<string>();
    private static int[] Ivs(PKM p) => [p.IV_HP, p.IV_ATK, p.IV_DEF, p.IV_SPA, p.IV_SPD, p.IV_SPE];
    private static PKM Target(SaveFile save, string location) => location == "party"
        ? save.GetPartySlotAtIndex(0) : save.GetBoxSlotAtIndex(0, 0);
    internal static void Put(SaveFile save, PKM p, string location)
    {
        p.RefreshChecksum();
        if (location == "party") save.WritePartySlot(p, save.Data.AsSpan(save.GetPartyOffset(0), 260));
        else save.WriteBoxSlot(p, save.Data.AsSpan(save.GetBoxSlotOffset(0, 0), 232));
    }
    internal static PKM Specimen(SaveFile save)
    {
        PKM p = save.Generation == 6 ? new PK6() : new PK7();
        p.Species = 25; p.PID = 0x12345678; p.EncryptionConstant = 0x76543210;
        p.TID16 = save.TID16; p.SID16 = save.SID16; p.OriginalTrainerName = save.OT;
        p.OriginalTrainerGender = save.Gender; p.Language = save.Language; p.Version = save.Version;
        p.CurrentLevel = 50; p.Nature = Nature.Adamant; p.Ability = 9; p.AbilityNumber = 1;
        p.MetLevel = 5; p.MetLocation = 6; p.MetDate = new DateOnly(2020, 1, 1);
        p.Move1 = 84; p.Move1_PP = 30; p.Ball = 4; p.Gender = 0; p.Nickname = "Pikachu";
        p.IV_HP = 3; p.IV_ATK = 5; p.IV_DEF = 7; p.IV_SPA = 9; p.IV_SPD = 11; p.IV_SPE = 13;
        p.EV_HP = 12; p.EV_ATK = 20; p.EV_DEF = 28; p.EV_SPA = 36; p.EV_SPD = 44; p.EV_SPE = 52;
        p.ResetPartyStats(); p.Stat_HPCurrent = 7; p.Status_Condition = 1;
        p.RefreshChecksum();
        return p;
    }
    internal static JsonObject Request(byte[] source, string location, string item, int? nature = null, string? stat = null)
    {
        var save = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
        var p = Target(save, location);
        return new JsonObject
        {
            ["schema_version"] = 1, ["source_base64"] = Convert.ToBase64String(source),
            ["intent"] = new JsonObject
            {
                ["game"] = save.Version.ToString(), ["expected_sha256"] = NativeWrite.Hash(source),
                ["trainer_key"] = NativeWrite.TrainerKey(save),
                ["mutation"] = new JsonObject
                {
                    ["kind"] = "virtual_training", ["item_code"] = item,
                    ["attempt"] = "a4740000-0000-4000-8000-000000000001", ["location"] = location,
                    ["box_index"] = location == "box" ? 0 : null, ["slot_index"] = 0,
                    ["expected_pokemon_sha256"] = NativeWrite.Hash(p.DecryptedBoxData),
                    ["expected_nature"] = (int)p.Nature, ["expected_ivs"] = JsonSerializer.SerializeToNode(Ivs(p)),
                    ["nature_id"] = nature, ["stat"] = stat,
                },
            },
        };
    }
    private static void Reject(JsonObject request, string label, bool verify = false, string? code = null)
    {
        var response = Execute(request, verify);
        Check(response["status"]!.GetValue<string>() == "rejected" && response["output_base64"] is null
            && Error(response) is not null && (code is null || Error(response) == code), label + ": " + Error(response));
    }
    private static (byte[], JsonObject) Accept(JsonObject request, string label)
    {
        var response = Execute(request);
        Check(response["status"]!.GetValue<string>() == "prepared", label + ": " + Error(response));
        var output = Convert.FromBase64String(response["output_base64"]!.GetValue<string>());
        var verify = Copy(request); verify["output_base64"] = Convert.ToBase64String(output);
        var verified = Execute(verify, true);
        Check(verified["status"]!.GetValue<string>() == "verified", label + " native verify " + Error(verified));
        Check(JsonNode.DeepEquals(verified["semantic_diff"], response["semantic_diff"]), label + " stable semantic diff");
        return (output, response);
    }

    public static void Run(string fixtureRoot, string outputRoot)
    {
        Directory.CreateDirectory(outputRoot);
        var report = new List<object>();
        foreach (string game in new[] { "X", "Y", "OR", "AS", "SN", "MN", "US", "UM" })
        {
            string sourcePath = Path.Combine(fixtureRoot, game, "prepared");
            var original = File.ReadAllBytes(sourcePath);
            string originalHash = NativeWrite.Hash(original);
            var derived = SaveUtil.GetVariantSAV((byte[])original.Clone())!;
            Check(derived.Version.ToString() == game, game + " contributor fixture game");
            var p = Specimen(derived);
            derived.SetBoxSlotAtIndex(p.Clone(), 0, 0);
            if (derived.PartyCount == 0) derived.PartyData = [p.Clone()];
            Put(derived, p.Clone(), "party");
            var source = derived.Write();
            var initial = Node(Inspection.Inspect(source));
            Check(initial["error"] is null, game + " disposable source valid: " + initial["error"]);
            int successful = 0;
            foreach (string location in new[] { "box", "party" })
            {
                var actual = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
                var before = Target(actual, location);
                var inspectRequest = new JsonObject { ["schema_version"] = 1,
                    ["source_base64"] = Convert.ToBase64String(source), ["location"] = location,
                    ["box_index"] = location == "box" ? 0 : null, ["slot_index"] = 0 };
                var inspected = Node(NativeTraining.Inspect(JsonSerializer.SerializeToUtf8Bytes(inspectRequest)));
                Check(inspected["status"]!.GetValue<string>() == "inspected", game + " target inspection " + Error(inspected));
                Check(inspected["output_base64"] is null && inspected["output_sha256"] is null, game + " inspection no output bytes");
                Check(inspected["semantic_diff"]!["pokemon_sha256"]!.GetValue<string>() == NativeWrite.Hash(before.DecryptedBoxData), game + " stored-PKM exact hash");
                Check(inspected["semantic_diff"]!["ivs"]!.AsArray().Select(n => n!.GetValue<int>()).SequenceEqual(Ivs(before)), game + " public IV ordering");
                foreach (int nature in Enumerable.Range(0, 25).Where(n => n != (int)before.Nature))
                {
                    var request = Request(source, location, "menta_naturaleza", nature);
                    var (output, response) = Accept(request, game + " " + location + " nature " + nature);
                    var changed = SaveUtil.GetVariantSAV((byte[])output.Clone())!;
                    var after = Target(changed, location);
                    Check((int)after.Nature == nature && after.StatNature == after.Nature, game + " actual Nature, no mint indirection");
                    Check(Ivs(after).SequenceEqual(Ivs(before)), game + " mint preserves all actual IVs");
                    AssertPokemon(before, after, location, true, game);
                    if (nature == ((int)before.Nature + 1) % 25) SaveCase(outputRoot, game, location, "mint", source, request, output, response);
                    successful++;
                }
                foreach (string stat in new[] { "hp", "atk", "defense", "spa", "spd", "spe" })
                {
                    var request = Request(source, location, "chapa_plateada", stat: stat);
                    var (output, response) = Accept(request, game + " " + location + " silver " + stat);
                    var changed = SaveUtil.GetVariantSAV((byte[])output.Clone())!;
                    var after = Target(changed, location);
                    var expected = Ivs(before); expected[Array.IndexOf(new[] { "hp", "atk", "defense", "spa", "spd", "spe" }, stat)] = 31;
                    Check(Ivs(after).SequenceEqual(expected) && after.Nature == before.Nature, game + " silver exactly one actual IV31");
                    AssertPokemon(before, after, location, false, game);
                    if (stat == "hp") SaveCase(outputRoot, game, location, "silver", source, request, output, response);
                    successful++;
                }
                var gold = Request(source, location, "chapa_dorada");
                var (goldBytes, goldResponse) = Accept(gold, game + " " + location + " gold");
                var goldSave = SaveUtil.GetVariantSAV((byte[])goldBytes.Clone())!;
                var goldPokemon = Target(goldSave, location);
                Check(Ivs(goldPokemon).All(iv => iv == 31) && goldPokemon.Nature == before.Nature, game + " gold all six actual IV31");
                AssertPokemon(before, goldPokemon, location, false, game);
                if (goldPokemon is IHyperTrain flags) Check(flags.HyperTrainFlags == 0, game + " no Hyper Training flags");
                Check(goldPokemon.CurrentLevel == 50, game + " no level100 requirement");
                SaveCase(outputRoot, game, location, "gold", source, gold, goldBytes, goldResponse);
                successful++;
                Reject(Request(source, location, "menta_naturaleza", (int)before.Nature), game + " mint no-op", code: "TRAINING_NO_CHANGE");
                Reject(Request(goldBytes, location, "chapa_plateada", stat: "hp"), game + " silver no-op", code: "TRAINING_NO_CHANGE");
                Reject(Request(goldBytes, location, "chapa_dorada"), game + " gold no-op", code: "TRAINING_NO_CHANGE");
                var altered = Copy(gold); altered["intent"]!["expected_sha256"] = new string('0',64);
                Reject(altered, game + " stale source", code: "STALE_SOURCE");
                altered = Copy(gold); altered["intent"]!["trainer_key"] = new string('0',64);
                Reject(altered, game + " wrong trainer", code: "WRONG_TRAINER");
                altered = Copy(gold); altered["intent"]!["game"] = game == "X" ? "Y" : "X";
                Reject(altered, game + " wrong title", code: "WRONG_GAME");
                altered = Copy(gold); altered["intent"]!["mutation"]!["expected_pokemon_sha256"] = new string('0',64);
                Reject(altered, game + " moved/replaced target", code: "STALE_MUTATION");
                altered = Copy(gold); altered["intent"]!["mutation"]!["expected_nature"] = 24;
                Reject(altered, game + " stale nature", code: "STALE_MUTATION");
                altered = Copy(gold); altered["intent"]!["mutation"]!["expected_ivs"]![0] = 0;
                Reject(altered, game + " stale IVs", code: "STALE_MUTATION");
                altered = Copy(gold); altered["intent"]!["mutation"]!["slot_index"] = 9999;
                Reject(altered, game + " invalid slot", code: "UNSAFE_TARGET");
                altered = Copy(gold); altered["intent"]!["mutation"]!["nature_id"] = 7;
                Reject(altered, game + " gold refuses extra nature", code: "INVALID_REQUEST");
                altered = Copy(gold); altered["intent"]!["mutation"]!["unexpected"] = true;
                Reject(altered, game + " unknown mutation field", code: "INVALID_REQUEST");
                altered = Copy(gold); altered["intent"]!["mutation"]!["attempt"] = "not-a-server-operation";
                Reject(altered, game + " invalid attempt", code: "INVALID_REQUEST");
                altered = Copy(gold); altered["output_base64"] = Convert.ToBase64String(source);
                Reject(altered, game + " unchanged output", true);
                // Forged output independently serialized with valid native checksums/signatures.
                foreach (string forgery in new[] { "money", "pid", "ec", "nature", "ev", "move", "status", "hp" })
                {
                    var forged = SaveUtil.GetVariantSAV((byte[])goldBytes.Clone())!;
                    if (forgery == "money") forged.Money = forged.Money == 1 ? 2u : 1u;
                    else
                    {
                        var pk = Target(forged, location);
                        switch (forgery)
                        {
                            case "pid": pk.PID ^= 1; break; case "ec": pk.EncryptionConstant ^= 1; break;
                            case "nature": pk.Nature = Nature.Modest; break; case "ev": pk.EV_HP++; break;
                            case "move": pk.Move1_PP--; break; case "status": pk.Status_Condition ^= 1; break;
                            case "hp": pk.Stat_HPCurrent++; break;
                        }
                        if (location == "box" && forgery is "status" or "hp") continue;
                        Put(forged, pk, location);
                    }
                    altered = Copy(gold); altered["output_base64"] = Convert.ToBase64String(forged.Write());
                    Reject(altered, game + " independent extra " + forgery, true);
                }
                var egg = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
                var eggPkm = Target(egg, location); eggPkm.IsEgg = true; Put(egg, eggPkm, location);
                Reject(Request(egg.Write(), location, "chapa_dorada"), game + " egg refused", code: "UNSAFE_TARGET");
            }
            Check(originalHash == NativeWrite.Hash(File.ReadAllBytes(sourcePath)), game + " public original untouched");
            report.Add(new { game, contributor_source_sha256 = originalHash, derived_sha256 = NativeWrite.Hash(source), transformations = successful });
            Console.WriteLine($"PASS TRAINING {game}: {successful} actual Nature/IV transformations, both storage locations and refusal/forgery checks");
        }
        EventRestrictions(fixtureRoot);
        File.WriteAllText(Path.Combine(outputRoot, "native-training-evidence.json"), JsonSerializer.Serialize(new
        {
            schema_version = 1, writer_version = NativeWrite.WriterVersion, checks, games = report,
            boundary = "Synthetic PKM on disposable retained-public-fixture copies only. Real-owner acceptance remains separate.",
        }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"RESULT OK; {checks} native training checks; all eight supported games");
    }

    private static void AssertPokemon(PKM before, PKM after, string location, bool mint, string game)
    {
        Check(after.PID == before.PID && after.EncryptionConstant == before.EncryptionConstant, game + " PID/EC stable");
        Check(after.TID16 == before.TID16 && after.SID16 == before.SID16 && after.OriginalTrainerName == before.OriginalTrainerName
            && after.Form == before.Form && after.Species == before.Species && after.IsShiny == before.IsShiny, game + " identity stable apart from authorized IV evidence");
        for (int i = 0; i < before.Data.Length; i++)
        {
            bool allowed = i is 6 or 7 || (mint ? i == 0x1C : i is >= 0x74 and <= 0x77)
                || location == "party" && i is >= 0xF2 and <= 0xFD;
            Check(allowed || before.Data[i] == after.Data[i], game + " unrelated PKM byte " + i);
        }
        if (location == "party")
            Check(before.Stat_HPCurrent == after.Stat_HPCurrent && before.Status_Condition == after.Status_Condition
                && before.Move1_PP == after.Move1_PP && before.Stat_Level == after.Stat_Level, game + " no healing or level change");
    }
    private static void SaveCase(string root, string game, string location, string item, byte[] source, JsonObject request, byte[] output, JsonObject response)
    {
        var folder = Path.Combine(root, game, location, item); Directory.CreateDirectory(folder);
        File.WriteAllBytes(Path.Combine(folder, "source"), source);
        File.WriteAllBytes(Path.Combine(folder, "expected"), output);
        File.WriteAllText(Path.Combine(folder, "request.json"), request.ToJsonString());
        File.WriteAllText(Path.Combine(folder, "response.json"), response.ToJsonString());
    }

    private static void EventRestrictions(string fixtureRoot)
    {
        foreach (string game in new[] { "X", "SN" })
        {
            var save = SaveUtil.GetVariantSAV(File.ReadAllBytes(Path.Combine(fixtureRoot, game, "prepared")))!;
            IEnumerable<MysteryGift> gifts = game == "X" ? EncounterEvent.MGDB_G6 : EncounterEvent.MGDB_G7;
            int natureCases = 0, ivCases = 0;
            foreach (var gift in gifts)
            {
                if (!gift.IsEntity) continue;
                PKM p;
                try { p = gift.ConvertToPKM(save, EncounterCriteria.Unrestricted); }
                catch { continue; }
                var legal = new LegalityAnalysis(p);
                if (!legal.Valid) continue;
                var derived = save.Clone(); Put(derived, p, "box"); var bytes = derived.Write();
                int fixedNature = gift is WC6 wc6 ? (int)wc6.Nature : (int)((WC7)gift).Nature;
                if (natureCases == 0 && fixedNature is >= 0 and < 25)
                {
                    var request = Request(bytes, "box", "menta_naturaleza", (fixedNature + 1) % 25);
                    var response = Execute(request);
                    if (Error(response) == "TRAINING_LEGALITY_UNSUPPORTED")
                    { Check(response["output_base64"] is null, game + " fixed event Nature refused without PID rewriting"); natureCases++; }
                }
                var fixedIvs = gift is WC6 w6 ? new[] { w6.IV_HP,w6.IV_ATK,w6.IV_DEF,w6.IV_SPA,w6.IV_SPD,w6.IV_SPE }
                    : new[] { ((WC7)gift).IV_HP,((WC7)gift).IV_ATK,((WC7)gift).IV_DEF,((WC7)gift).IV_SPA,((WC7)gift).IV_SPD,((WC7)gift).IV_SPE };
                int index = Array.FindIndex(fixedIvs, x => x is >= 0 and < 31);
                if (ivCases == 0 && index >= 0)
                {
                    var request = Request(bytes, "box", "chapa_plateada", stat: new[] { "hp","atk","defense","spa","spd","spe" }[index]);
                    var response = Execute(request);
                    if (Error(response) == "TRAINING_LEGALITY_UNSUPPORTED")
                    { Check(response["output_base64"] is null, game + " fixed event IV refused without identity rewriting"); ivCases++; }
                }
                if (natureCases > 0 && ivCases > 0) break;
            }
            Check(natureCases > 0 && ivCases > 0, game + " actual pinned event restrictions tested for Nature and IVs");
        }
    }

    public static void SignatureRegression(string trainingFixtureRoot, string outputRoot)
    {
        Directory.CreateDirectory(outputRoot);
        int correctedVerifierCases = 0, generatedSignRepairs = 0;
        var examples = new List<object>();
        // The existing publicly distributed verification modulus, not a signing key.
        var modulus = new BigInteger(Convert.FromHexString(
            "B61E192091F90A8F76A6EAAA9A3CE58C863F39AE253F037816F5975854E07A9A456601E7C94C29759FE155C064EDDFA111443F81EF1A428CF6CD32F9DAC9D48E94CFB3F690120E8E6B9111ADDAF11E7C96208C37C0143FF2BF3D7E831141A973"), true, true);
        foreach (string game in new[] { "SN", "MN", "US", "UM" })
        {
            var source = File.ReadAllBytes(Path.Combine(trainingFixtureRoot, game, "party", "mint", "source"));
            var original = SaveUtil.GetVariantSAV((byte[])source.Clone())!;
            var before = original.GetPartySlotAtIndex(0);
            foreach (int nature in Enumerable.Range(0,25).Where(n => n != (int)before.Nature))
            {
                var request = Request(source, "party", "menta_naturaleza", nature);
                var prepared = Execute(request);
                Check(prepared["status"]!.GetValue<string>() == "prepared", game + " signature case prepared " + Error(prepared));
                var output = Convert.FromBase64String(prepared["output_base64"]!.GetValue<string>());
                Check(NativeSignature.VerifySave(output), game + " corrected verifier retains full chain");
                int start = (game is "US" or "UM" ? 0x6C000 : 0x6BA00) + MemeCrypto.SaveFileSignatureOffset;
                var signature = output.AsSpan(start, MemeCrypto.SaveFileSignatureLength);
                var tableHash = SHA256.HashData(output.AsSpan(output.Length - 0x200, game is "US" or "UM" ? 0x150 : 0x140));
                bool oldValid = MemeCrypto.VerifyMemeData(signature, out var oldDecoded, MemeKeyIndex.PokedexAndSaveFile)
                    && oldDecoded.AsSpan(0,32).SequenceEqual(tableHash);
                if (!oldValid)
                {
                    int publicResultBytes = BigInteger.ModPow(new BigInteger(signature[^96..],true,true),65537,modulus).ToByteArray(true,true).Length;
                    Check(publicResultBytes < 96, game + " failure specifically short RSA public output, not bad signature");
                    correctedVerifierCases++;
                    var example = Path.Combine(outputRoot,$"{game}-nature-{nature}"); Directory.CreateDirectory(example);
                    File.WriteAllBytes(Path.Combine(example,"valid-save"),output);
                    examples.Add(new { game, nature, rsa_public_bytes = publicResultBytes, native_signature_valid = true,
                        pinned_verifier_false_negative = true, source_sha256 = NativeWrite.Hash(source), output_sha256 = NativeWrite.Hash(output) });
                }
                // Rebuild the same intended output independently with the pinned
                // serializer. Differences, if any, must be its short RSA suffix.
                var independent = original.Clone(); var pk = before.Clone(); pk.Nature = (Nature)nature;
                var oldStats = before.GetStats(before.PersonalInfo); var newStats = pk.GetStats(pk.PersonalInfo);
                if(oldStats[0]!=newStats[0])pk.Stat_HPMax=newStats[0];
                if(oldStats[1]!=newStats[1])pk.Stat_ATK=newStats[1];
                if(oldStats[2]!=newStats[2])pk.Stat_DEF=newStats[2];
                if(oldStats[3]!=newStats[3])pk.Stat_SPE=newStats[3];
                if(oldStats[4]!=newStats[4])pk.Stat_SPA=newStats[4];
                if(oldStats[5]!=newStats[5])pk.Stat_SPD=newStats[5];
                Put(independent,pk,"party"); var raw=independent.Write();
                if(!raw.AsSpan().SequenceEqual(output))
                {
                    Check(!NativeSignature.VerifySave(raw),game+" malformed generated signature rejected");
                    for(int i=0;i<raw.Length;i++) Check(raw[i]==output[i] || i>=start+32 && i<start+128,game+" repair confined to RSA suffix");
                    int padding = 0; while(padding<95 && output[start+32+padding]==0)padding++;
                    Check(padding>0 && raw.AsSpan(start+32,96-padding).SequenceEqual(output.AsSpan(start+32+padding,96-padding)),game+" actual left-padding correction");
                    generatedSignRepairs++;
                }
                foreach(int relative in new[]{0,31,32,64,127})
                {
                    var corrupt=(byte[])output.Clone();corrupt[start+relative]^=1;
                    Check(!NativeSignature.VerifySave(corrupt),game+" signature forgery refused "+relative);
                    Check(Node(Inspection.Inspect(corrupt))["error"]!.GetValue<string>()=="CORRUPT_SAVE",game+" full parser refuses signature forgery");
                }
                var wrongTable=(byte[])output.Clone();wrongTable[wrongTable.Length-0x200+20]^=1;
                Check(!NativeSignature.VerifySave(wrongTable),game+" checksum table binding retained");
            }
        }
        if (generatedSignRepairs == 0)
        {
            var baseBytes=File.ReadAllBytes(Path.Combine(trainingFixtureRoot,"SN","party","mint","source"));
            for(int nonce=1;nonce<=4096 && generatedSignRepairs==0;nonce++)
            {
                var baseline=SaveUtil.GetVariantSAV((byte[])baseBytes.Clone())!;
                var originalPk=baseline.GetPartySlotAtIndex(0);originalPk.EncryptionConstant+=(uint)nonce;
                Put(baseline,originalPk,"party");var source=baseline.Write();
                if(!NativeSignature.VerifySave(source))continue; // Invalid derived fixture is never submitted.
                var before=SaveUtil.GetVariantSAV((byte[])source.Clone())!.GetPartySlotAtIndex(0);
                var independent=SaveUtil.GetVariantSAV((byte[])source.Clone())!;
                var pk=before.Clone();pk.Nature=Nature.Modest;
                var oldStats=before.GetStats(before.PersonalInfo);var newStats=pk.GetStats(pk.PersonalInfo);
                if(oldStats[1]!=newStats[1])pk.Stat_ATK=newStats[1];
                if(oldStats[2]!=newStats[2])pk.Stat_DEF=newStats[2];
                if(oldStats[3]!=newStats[3])pk.Stat_SPE=newStats[3];
                if(oldStats[4]!=newStats[4])pk.Stat_SPA=newStats[4];
                if(oldStats[5]!=newStats[5])pk.Stat_SPD=newStats[5];
                Put(independent,pk,"party");var raw=independent.Write();
                if(NativeSignature.VerifySave(raw))continue;
                var request=Request(source,"party","menta_naturaleza",(int)Nature.Modest);
                var(output,response)=Accept(request,"short generated RSA signature normalized");
                Check(NativeSignature.VerifySave(output),"repaired generated signature independently valid");
                int start=0x6BA00+MemeCrypto.SaveFileSignatureOffset;
                int padding=0;while(padding<95 && output[start+32+padding]==0)padding++;
                Check(padding>0 && raw.AsSpan(start+32,96-padding).SequenceEqual(output.AsSpan(start+32+padding,96-padding)),"actual generated private-RSA result was short and left-aligned");
                for(int i=0;i<raw.Length;i++)Check(raw[i]==output[i] || i>=start+32 && i<start+128,"private-RSA repair changes only its suffix");
                var example=Path.Combine(outputRoot,"SN-generated-short-signature");Directory.CreateDirectory(example);
                File.WriteAllBytes(Path.Combine(example,"source"),source);
                File.WriteAllBytes(Path.Combine(example,"pinned-invalid-output"),raw);
                File.WriteAllBytes(Path.Combine(example,"verified-output"),output);
                File.WriteAllText(Path.Combine(example,"request.json"),request.ToJsonString());
                examples.Add(new{game="SN",nonce,rsa_sign_padding_bytes=padding,generated_signature_repaired=true,
                    output_sha256=NativeWrite.Hash(output)});
                generatedSignRepairs++;
            }
        }
        Check(correctedVerifierCases>0,"real pinned public-verifier padding regressions exercised");
        Check(generatedSignRepairs>0,"real generated private-RSA padding regression exercised");
        File.WriteAllText(Path.Combine(outputRoot,"signature-padding-evidence.json"),JsonSerializer.Serialize(new
        {
            schema_version=1,corrected_verifier_cases=correctedVerifierCases,generated_sign_repairs=generatedSignRepairs,checks,examples,
            boundary="Same public key, RSA/AES/SHA1/checksum-table-SHA256 verification. No private signing key copied; no validation bypass.",
        },new JsonSerializerOptions{WriteIndented=true}));
        Console.WriteLine($"RESULT OK; {checks} signature assertions; {correctedVerifierCases} pinned false-negative public-RSA padding cases; {generatedSignRepairs} generated-signature left-padding repairs");
    }

    public static void ExportServiceFixtures(string matrixRoot, string outputRoot)
    {
        Directory.CreateDirectory(outputRoot);
        var evidence=new List<object>();
        foreach(string game in new[]{"X","Y","OR","AS","SN","MN","US","UM"})
        {
            var input=File.ReadAllBytes(Path.Combine(matrixRoot,game,"party","silver","source"));
            var save=SaveUtil.GetVariantSAV((byte[])input.Clone())!;
            var target=save.GetPartySlotAtIndex(0);
            int removed=0;
            for(int box=0;box<save.BoxCount;box++)for(int slot=0;slot<save.BoxSlotCount;slot++)
            {
                var other=save.GetBoxSlotAtIndex(box,slot);
                if(other.Species==0 || other.PID!=target.PID && other.EncryptionConstant!=target.EncryptionConstant)continue;
                save.WriteBoxSlot(save.BlankPKM,save.Data.AsSpan(save.GetBoxSlotOffset(box,slot),232));removed++;
            }
            Check(removed==1,game+" exactly synthetic duplicate box specimen removed");
            var source=save.Write();
            for(int nonce=1;save is SAV7 && !NativeSignature.VerifySave(source) && nonce<512;nonce++)
            {
                // Fixture generation only: choose a different synthetic EC if
                // the pinned serializer emits its known short-RSA artifact.
                target.EncryptionConstant++;Put(save,target,"party");source=save.Write();
            }
            Check(Node(Inspection.Inspect(source))["error"] is null,game+" service fixture has valid native integrity");
            var verified=SaveUtil.GetVariantSAV((byte[])source.Clone())!;
            target=verified.GetPartySlotAtIndex(0);
            int collisions=verified.BoxData.Concat(verified.PartyData).Count(p=>p.Species!=0 &&
                (p.PID==target.PID || p.EncryptionConstant==target.EncryptionConstant));
            Check(collisions==1,game+" service target unique PID and EC");
            Check(target.TID16==verified.TID16 && target.SID16==verified.SID16 &&
                target.OriginalTrainerName==verified.OT && target.OriginalTrainerGender==verified.Gender &&
                target.Language==verified.Language && !target.IsEgg,game+" own OT non-egg source");
            foreach(var(effect,item,nature,stat) in new (string,string,int?,string?)[]{
                ("mint","menta_naturaleza",((int)target.Nature+1)%25,null),
                ("silver","chapa_plateada",null,"hp"),("gold","chapa_dorada",null,null)})
            {
                var request=Request(source,"party",item,nature,stat);
                var(output,response)=Accept(request,game+" unique service "+effect);
                SaveCase(outputRoot,game,"party",effect,source,request,output,response);
            }
            evidence.Add(new{game,source_sha256=NativeWrite.Hash(source),source_party_slot=1,unique_pid_ec=true,
                removed_synthetic_duplicates=removed,own_ot=true});
        }
        File.WriteAllText(Path.Combine(outputRoot,"native-service-fixtures.json"),JsonSerializer.Serialize(new
        {schema_version=1,games=evidence,checks,boundary="Derived public-fixture copies with one unambiguous own-OT synthetic party target. No owner data."},
            new JsonSerializerOptions{WriteIndented=true}));
        Console.WriteLine($"RESULT OK; {checks} native service fixture assertions; eight unique party targets, three virtual consumables each");
    }

    public static void ExportForeignFixture(string serviceRoot, string outputRoot)
    {
        Directory.CreateDirectory(outputRoot);
        var donor=File.ReadAllBytes(Path.Combine(serviceRoot,"Y","party","silver","source"));
        var save=SaveUtil.GetVariantSAV((byte[])donor.Clone())!;
        var original=save.GetPartySlotAtIndex(0);
        save.OT="Destino Fixture";save.TID16=24680;save.SID16=13579;save.Gender=1;
        var received=save.Write().ToArray();
        Check(Node(Inspection.Inspect(received))["error"] is null,"foreign received fixture native integrity");
        Check(save.GetPartySlotAtIndex(0).DecryptedBoxData.AsSpan().SequenceEqual(original.DecryptedBoxData),"foreign fixture retains exact original PKM");
        save.PartyData=[];
        for(int box=0;box<save.BoxCount;box++)for(int slot=0;slot<save.BoxSlotCount;slot++)
            save.WriteBoxSlot(save.BlankPKM,save.Data.AsSpan(save.GetBoxSlotOffset(box,slot),232));
        var empty=save.Write().ToArray();
        Check(Node(Inspection.Inspect(empty))["error"] is null,"empty recipient fixture native integrity");
        Check(save.PartyCount==0 && save.BoxData.All(p=>p.Species==0),"recipient starts with no Pokemon identity");
        File.WriteAllBytes(Path.Combine(outputRoot,"donor-source"),donor);
        File.WriteAllBytes(Path.Combine(outputRoot,"recipient-empty"),empty);
        File.WriteAllBytes(Path.Combine(outputRoot,"recipient-received"),received);
        File.WriteAllText(Path.Combine(outputRoot,"foreign-fixture.json"),JsonSerializer.Serialize(new
        {
            schema_version=1,game="Y",party_slot=1,target_pid=original.PID,target_ec=original.EncryptionConstant,
            donor_sha256=NativeWrite.Hash(donor),empty_sha256=NativeWrite.Hash(empty),received_sha256=NativeWrite.Hash(received),
            boundary="Disposable synthetic own-OT specimen moved only relationally in the SQL gate; not physical robbery certification.",
        },new JsonSerializerOptions{WriteIndented=true}));
        Console.WriteLine($"RESULT OK; {checks} foreign fixture assertions; donor and recipient native copies only");
    }
}
