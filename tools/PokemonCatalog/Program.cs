using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using PKHeX.Core;

// Export embedded resources, not mutable GameInfo UI labels or online caches.
// Array offsets retain PKHeX/game IDs, including empty/reserved entries.
if (args.Length != 1) throw new ArgumentException("Expected output JSON path");
var assembly = typeof(PKM).Assembly;
var resources = new SortedDictionary<string, string>(StringComparer.Ordinal);
string[] Read(string name, string language)
{
    var suffix = $".text_{name}_{language}.txt";
    var resource = assembly.GetManifestResourceNames().Single(n => n.EndsWith(suffix, StringComparison.Ordinal));
    using var stream = assembly.GetManifestResourceStream(resource)!;
    using var bytes = new MemoryStream();
    stream.CopyTo(bytes);
    resources[resource] = Convert.ToHexString(SHA256.HashData(bytes.ToArray())).ToLowerInvariant();
    bytes.Position = 0;
    using var reader = new StreamReader(bytes, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
    var lines = new List<string>();
    while (reader.ReadLine() is { } line) lines.Add(line);
    return lines.ToArray();
}
var categories = new SortedDictionary<string, object>(StringComparer.Ordinal);
var xy = new SAV7USUM();
var maximumIds = new SortedDictionary<string, int>(StringComparer.Ordinal) {
    ["species"] = xy.MaxSpeciesID, ["move"] = xy.MaxMoveID,
    ["ability"] = xy.MaxAbilityID, ["item"] = xy.MaxItemID,
    ["item3"] = new SAV3E().MaxItemID, ["nature"] = 24, ["type"] = (int)MoveType.Fairy,
};
foreach (var (key, resource) in new[] {
    ("species", "Species"), ("move", "Moves"), ("ability", "Abilities"),
    ("item", "Items"), ("item3", "ItemsG3"), ("type", "Types"), ("nature", "Natures"),
})
{
    var en = Read(resource, "en");
    var es = Read(resource, "es");
    if (en.Length != es.Length) throw new InvalidDataException($"Mismatched {key} resources");
    // Ship Gen3-7 through Ultra Sun/Ultra Moon, not later-game catalogs.
    var count = maximumIds[key] + 1;
    categories[key] = new { en = en.Take(count).ToArray(), es = es.Take(count).ToArray() };
}
var result = new {
    schema = 1,
    source = "PKHeX.Core 24.11.11 embedded English/Spanish name resources",
    // No flavor text is present in these resources. Do not fabricate descriptions.
    descriptions = "unavailable",
    maximumIds,
    resources,
    categories,
};
var json = JsonSerializer.Serialize(result, new JsonSerializerOptions {
    WriteIndented = true, Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
}).Replace("\r\n", "\n") + "\n";
File.WriteAllText(args[0], json, new UTF8Encoding(false));
Console.WriteLine($"Exported {categories.Count} name categories; {resources.Count} hashed resources.");
