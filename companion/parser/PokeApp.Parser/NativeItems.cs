using PKHeX.Core;
using System.Text.Json;
using static PokeApp.Parser.NativeWrite;

namespace PokeApp.Parser;

// Owner-approved quick items: Rare Candy and Heart Scale only, X..UM. Only the
// bag block, its checksum and the existing Gen7 signature may change; every box
// and party Pokemon and every other inventory entry must be preserved exactly.
public static class NativeItems
{
    internal static readonly Dictionary<string, ushort> Items = new()
    {
        ["rare_candy"] = 50,
        ["heart_scale"] = 93,
    };
    private static readonly HashSet<string> Games = ["X", "Y", "OR", "AS", "SN", "MN", "US", "UM"];

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
            Exact(root, ["schema_version", "source_base64"]);
            if (Integer(root, "schema_version") != 1) throw new Rejection("INVALID_REQUEST");
            var original = Bytes(root, "source_base64");
            var save = Gen67(original);
            var pouches = save.Inventory;
            var items = new Dictionary<string, object>();
            foreach (var (name, id) in Items)
            {
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
        Exact(m, ["kind", "item", "quantity", "expected_count"]);
        var name = Text(m, "item");
        if (Text(m, "kind") != "add_item" || !Items.TryGetValue(name, out var id)) throw new Rejection("UNSAFE_TARGET");
        int quantity = Integer(m, "quantity"), expected = Integer(m, "expected_count");
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
            SemanticDiff = new
            {
                Kind = "add_item", Item = name, Quantity = quantity, ExpectedCount = expected,
                PreservedUnrelated = true, ChecksumsValid = true, SignatureValid = true,
            },
        };
    }
}
