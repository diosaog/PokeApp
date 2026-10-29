using PKHeX.Core;
using System.Text.Json;
using static PokeApp.Parser.NativeWrite;

namespace PokeApp.Parser;

// Owner-approved quick items: Rare Candy and Heart Scale only, X..UM. Only the
// bag block, its checksum and the existing Gen7 signature may change; every box
// and party Pokemon and every other inventory entry must be preserved exactly.
// 072: a paid Shop object (deliver_item) is one unit of an object in ShopItems,
// under the same byte checks; the server spends the purchase once.
public static class NativeItems
{
    internal static readonly Dictionary<string, ushort> Items = new()
    {
        ["rare_candy"] = 50,
        ["heart_scale"] = 93,
    };
    // Equal to BAG_ITEMS in app/domain/shop_item_uses.py (a test compares them).
    public static readonly IReadOnlyDictionary<string, ushort> ShopItems = new Dictionary<string, ushort>
    {
        ["cheri_berry"] = 149, ["chesto_berry"] = 150, ["pecha_berry"] = 151, ["rawst_berry"] = 152,
        ["aspear_berry"] = 153, ["oran_berry"] = 155, ["persim_berry"] = 156, ["sitrus_berry"] = 158,
        ["occa_berry"] = 184, ["passho_berry"] = 185, ["wacan_berry"] = 186, ["rindo_berry"] = 187,
        ["yache_berry"] = 188, ["chople_berry"] = 189, ["kebia_berry"] = 190, ["shuca_berry"] = 191,
        ["coba_berry"] = 192, ["payapa_berry"] = 193, ["tanga_berry"] = 194, ["charti_berry"] = 195,
        ["kasib_berry"] = 196, ["haban_berry"] = 197, ["colbur_berry"] = 198, ["babiri_berry"] = 199,
        ["chilan_berry"] = 200, ["liechi_berry"] = 201, ["ganlon_berry"] = 202, ["salac_berry"] = 203,
        ["petaya_berry"] = 204, ["apicot_berry"] = 205, ["lansat_berry"] = 206, ["starf_berry"] = 207,
        ["choice_specs"] = 297, ["choice_band"] = 220, ["choice_scarf"] = 287, ["leftovers"] = 234,
        ["focus_sash"] = 275, ["life_orb"] = 270, ["eviolite"] = 538, ["rocky_helmet"] = 540,
        ["air_balloon"] = 541, ["eject_button"] = 547, ["red_card"] = 542, ["white_herb"] = 214,
        ["kings_rock"] = 221, ["scope_lens"] = 232, ["zoom_lens"] = 276, ["toxic_orb"] = 272,
        ["flame_orb"] = 273,
        ["fire_gem"] = 548, ["water_gem"] = 549, ["electric_gem"] = 550, ["grass_gem"] = 551,
        ["ice_gem"] = 552, ["fighting_gem"] = 553, ["poison_gem"] = 554, ["ground_gem"] = 555,
        ["flying_gem"] = 556, ["psychic_gem"] = 557, ["bug_gem"] = 558, ["rock_gem"] = 559,
        ["ghost_gem"] = 560, ["dragon_gem"] = 561, ["dark_gem"] = 562, ["steel_gem"] = 563,
        ["normal_gem"] = 564, ["fairy_gem"] = 715,
        ["silk_scarf"] = 251, ["charcoal"] = 249, ["mystic_water"] = 243, ["magnet"] = 242,
        ["miracle_seed"] = 239, ["never_melt_ice"] = 246, ["black_belt"] = 241, ["poison_barb"] = 245,
        ["soft_sand"] = 237, ["sharp_beak"] = 244, ["twisted_spoon"] = 248, ["silver_powder"] = 222,
        ["hard_stone"] = 238, ["spell_tag"] = 247, ["dragon_fang"] = 250, ["black_glasses"] = 240,
        ["metal_coat"] = 233, ["pixie_plate"] = 644,
        ["ability_capsule"] = 645, ["bottle_cap"] = 795, ["gold_bottle_cap"] = 796,
        ["sun_stone"] = 80, ["moon_stone"] = 81, ["fire_stone"] = 82, ["thunder_stone"] = 83,
        ["water_stone"] = 84, ["leaf_stone"] = 85, ["shiny_stone"] = 107, ["dusk_stone"] = 108,
        ["dawn_stone"] = 109, ["ice_stone"] = 849, ["oval_stone"] = 110, ["dragon_scale"] = 235,
        ["upgrade"] = 252, ["protector"] = 321, ["electirizer"] = 322, ["magmarizer"] = 323,
        ["dubious_disc"] = 324, ["reaper_cloth"] = 325, ["razor_claw"] = 326, ["razor_fang"] = 327,
        ["deep_sea_tooth"] = 226, ["deep_sea_scale"] = 227, ["prism_scale"] = 537,
        ["whipped_dream"] = 646, ["sachet"] = 647,
        ["root_fossil"] = 99, ["claw_fossil"] = 100, ["helix_fossil"] = 101, ["dome_fossil"] = 102,
        ["old_amber"] = 103, ["armor_fossil"] = 104, ["skull_fossil"] = 105, ["cover_fossil"] = 572,
        ["plume_fossil"] = 573, ["jaw_fossil"] = 710, ["sail_fossil"] = 711,
    };
    private static readonly HashSet<string> Games = ["X", "Y", "OR", "AS", "SN", "MN", "US", "UM"];

    private static bool Known(string name, out ushort id)
        => Items.TryGetValue(name, out id) || ShopItems.TryGetValue(name, out id);

    // Optional `items`: up to 8 distinct known names (default: the quick items).
    private static string[] Requested(JsonElement root)
    {
        if (!root.TryGetProperty("items", out var list)) return [.. Items.Keys];
        if (list.ValueKind != JsonValueKind.Array || list.GetArrayLength() is 0 or > 8)
            throw new Rejection("INVALID_REQUEST");
        var names = list.EnumerateArray().Select(e => e.ValueKind == JsonValueKind.String ? e.GetString()! : "").ToArray();
        if (names.Distinct(StringComparer.Ordinal).Count() != names.Length || names.Any(n => !Known(n, out _)))
            throw new Rejection("INVALID_REQUEST");
        return names;
    }

    private static bool IsUuid(string value)
        => value.Length == 36 && Guid.TryParseExact(value, "D", out var g) && g.ToString("D") == value;

    private static SAV_BEEF Gen67(byte[] bytes)
    {
        var save = Validate(bytes);
        if (!Games.Contains(save.Version.ToString())) throw new Rejection("UNSUPPORTED_FORMAT");
        return save;
    }

    private static (int pouch, InventoryItem? slot) Find(IReadOnlyList<InventoryPouch> pouches, ushort id)
    {
        var candidates = Enumerable.Range(0, pouches.Count).Where(i => pouches[i].CanContain(id)).ToArray();
        if (candidates.Length != 1) throw new Rejection("UNSUPPORTED_FORMAT");
        var slots = pouches[candidates[0]].Items.Where(i => i.Index == id).ToArray();
        if (slots.Length > 1) throw new Rejection("UNSAFE_TARGET");
        return (candidates[0], slots.FirstOrDefault());
    }

    private static object Describe(InventoryPouch pouch, InventoryItem? slot)
    {
        int count = slot?.Count ?? 0;
        bool room = slot is not null || pouch.Items.Any(i => i.Index == 0);
        return new { Count = count, Max = pouch.MaxCount, Addable = room ? Math.Max(0, pouch.MaxCount - count) : 0 };
    }

    public static object Inventory(ReadOnlySpan<byte> request)
    {
        try
        {
            if (request.Length is 0 or > MaxRequestBytes) throw new Rejection("INVALID_REQUEST");
            using var document = JsonDocument.Parse(request.ToArray(), new JsonDocumentOptions { MaxDepth = 4 });
            var root = document.RootElement;
            Exact(root, root.TryGetProperty("items", out _) ? ["schema_version", "source_base64", "items"]
                                                            : ["schema_version", "source_base64"]);
            if (Integer(root, "schema_version") != 1) throw new Rejection("INVALID_REQUEST");
            var names = Requested(root);
            var original = Bytes(root, "source_base64");
            var save = Gen67(original);
            var pouches = save.Inventory;
            var items = new Dictionary<string, object>();
            foreach (var name in names)
            {
                Known(name, out var id);
                // An object this game's bag cannot hold reads as max 0.
                if (!pouches.Any(p => p.CanContain(id))) { items[name] = new { Count = 0, Max = 0, Addable = 0 }; continue; }
                var (pouch, slot) = Find(pouches, id);
                items[name] = Describe(pouches[pouch], slot);
            }
            return new
            {
                SchemaVersion = 1, WriterVersion, Status = "inspected", Error = (string?)null,
                Game = save.Version.ToString(), TrainerKey = TrainerKey(save), SourceSha256 = Hash(original),
                OutputSha256 = (string?)null, OutputBase64 = (string?)null, SemanticDiff = items,
            };
        }
        catch (Rejection e) { return Failure(e.Code); }
        catch (JsonException) { return Failure("INVALID_REQUEST"); }
        catch (FormatException) { return Failure("INVALID_REQUEST"); }
        catch (Exception) { return Failure("WRITE_PREPARATION_FAILED"); }
    }

    internal static object Execute(JsonElement root, bool verify)
    {
        var intent = root.GetProperty("intent");
        Exact(intent, ["game", "expected_sha256", "trainer_key", "mutation"]);
        var m = intent.GetProperty("mutation");
        var kind = Text(m, "kind");
        bool delivery = kind == "deliver_item";
        Exact(m, delivery ? ["kind", "item", "quantity", "expected_count", "purchase_id", "attempt"]
                          : ["kind", "item", "quantity", "expected_count"]);
        var name = Text(m, "item");
        ushort id = 0;
        if (delivery ? !ShopItems.TryGetValue(name, out id) : kind != "add_item" || !Items.TryGetValue(name, out id))
            throw new Rejection("UNSAFE_TARGET");
        int quantity = Integer(m, "quantity"), expected = Integer(m, "expected_count");
        string? purchase = delivery ? Text(m, "purchase_id") : null, attempt = delivery ? Text(m, "attempt") : null;
        // One purchase is one object.
        if (delivery && (!IsUuid(purchase!) || !IsUuid(attempt!))) throw new Rejection("INVALID_REQUEST");
        if (delivery && quantity != 1) throw new Rejection("INVENTORY_LIMIT");
        var original = Bytes(root, "source_base64");
        var source = Gen67(original);
        var game = Text(intent, "game");
        var trainer = Text(intent, "trainer_key");
        if (Hash(original) != Text(intent, "expected_sha256")) throw new Rejection("STALE_SOURCE");
        if (game != source.Version.ToString()) throw new Rejection("WRONG_GAME");
        if (trainer != TrainerKey(source)) throw new Rejection("WRONG_TRAINER");

        var before = source.Inventory;
        var (index, slot) = Find(before, id);
        var pouch = before[index];
        int current = slot?.Count ?? 0;
        if (current != expected) throw new Rejection("STALE_MUTATION");
        if (quantity < 1 || quantity > pouch.MaxCount - current) throw new Rejection("INVENTORY_LIMIT");
        if (slot is null && !pouch.Items.Any(i => i.Index == 0)) throw new Rejection("INVENTORY_FULL");

        var clone = source.Clone();
        var pouches = clone.Inventory;
        var (_, target) = Find(pouches, id);
        if (target is null)
        {
            target = pouches[index].Items.First(i => i.Index == 0);
            target.Index = id;
            target.SetNewDetails(quantity);
        }
        target.Count = current + quantity;
        clone.Inventory = pouches;
        var expectedOutput = clone.Write();
        byte[] output = verify ? Bytes(root, "output_base64") : expectedOutput;
        if (original.Length != output.Length || original.AsSpan().SequenceEqual(output)
            || !output.AsSpan().SequenceEqual(expectedOutput)) throw new Rejection("UNEXPECTED_DIFF");

        var result = Gen67(output);
        if (result.Version.ToString() != game || TrainerKey(result) != trainer) throw new Rejection("VERIFICATION_FAILED");
        var after = result.Inventory;
        if (after.Count != before.Count) throw new Rejection("VERIFICATION_FAILED");
        for (int p = 0; p < before.Count; p++)
        {
            var old = before[p].Items.Where(i => i.Index != 0 && !(p == index && i.Index == id)).Select(i => (i.Index, i.Count));
            var now = after[p].Items.Where(i => i.Index != 0 && !(p == index && i.Index == id)).Select(i => (i.Index, i.Count));
            if (!old.SequenceEqual(now)) throw new Rejection("UNEXPECTED_DIFF");
        }
        var added = after[index].Items.Where(i => i.Index == id).ToArray();
        if (added.Length != 1 || added[0].Count != current + quantity) throw new Rejection("VERIFICATION_FAILED");
        if (!source.BoxData.Zip(result.BoxData).All(x => x.First.Data.AsSpan().SequenceEqual(x.Second.Data))
            || !source.PartyData.Zip(result.PartyData).All(x => x.First.Data.AsSpan().SequenceEqual(x.Second.Data))
            || source.PartyCount != result.PartyCount || source.Money != result.Money)
            throw new Rejection("UNEXPECTED_DIFF");

        // Bytes: one save block (the bag), that block's checksum, Gen7 signature.
        int sig = source is SAV7USUM ? 0x6C000 + MemeCrypto.SaveFileSignatureOffset
                : source is SAV7SM ? 0x6BA00 + MemeCrypto.SaveFileSignatureOffset : -1;
        bool Signature(int i) => sig >= 0 && i >= sig && i < sig + MemeCrypto.SaveFileSignatureLength;
        var table = original.Length - 0x200;
        var changed = Enumerable.Range(0, original.Length).Where(i => original[i] != output[i] && !Signature(i)).ToArray();
        var data = changed.Where(i => i < table).ToArray();
        if (data.Length == 0) throw new Rejection("UNEXPECTED_DIFF");
        var blocks = source.AllBlocks.Where(b => data[0] >= b.Offset && data[0] < b.Offset + b.Length).ToArray();
        if (blocks.Length != 1) throw new Rejection("UNSUPPORTED_FORMAT");
        var block = blocks[0];
        int checksum = table + 0x14 + checked((int)block.ID * 8) + 6;
        if (changed.Any(i => !(i >= block.Offset && i < block.Offset + block.Length) && i != checksum && i != checksum + 1))
            throw new Rejection("UNEXPECTED_DIFF");

        return new
        {
            SchemaVersion = 1, WriterVersion, Status = verify ? "verified" : "prepared", Error = (string?)null,
            Game = game, TrainerKey = trainer, SourceSha256 = Hash(original), OutputSha256 = Hash(output),
            OutputBase64 = verify ? null : Convert.ToBase64String(output),
            SemanticDiff = delivery
                ? new
                {
                    Kind = kind, Item = name, Quantity = quantity, ExpectedCount = expected,
                    PurchaseId = purchase, Attempt = attempt,
                    PreservedUnrelated = true, ChecksumsValid = true, SignatureValid = true,
                }
                : (object)new
                {
                    Kind = "add_item", Item = name, Quantity = quantity, ExpectedCount = expected,
                    PreservedUnrelated = true, ChecksumsValid = true, SignatureValid = true,
                },
        };
    }
}
