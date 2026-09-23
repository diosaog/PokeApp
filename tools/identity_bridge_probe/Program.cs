using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using PKHeX.Core;

// In-memory PKM only. Never opens a save or calls the bridge command dispatcher.
internal static class IdentityBridgeProbe
{
    private static void Set(object p, string name, object value)
    {
        var prop = p.GetType().GetProperty(name)!;
        prop.SetValue(p, prop.PropertyType.IsEnum
            ? Enum.ToObject(prop.PropertyType, value) : Convert.ChangeType(value, prop.PropertyType));
    }

    public static void Main()
    {
        var assembly = typeof(PKM).Assembly;
        var export = typeof(PKHeXBridgeApp.Bridge).GetMethod("PkmToDto", BindingFlags.NonPublic | BindingFlags.Static)!;
        var rows = new List<object>();
        foreach (PKM p in new PKM[] { new PK3(), new PK4(), new PK5() })
        {
            foreach (var pair in new Dictionary<string, object> {
                ["Species"] = 92, ["PID"] = 123456789u, ["TID16"] = 12345,
                ["SID16"] = 6789, ["Language"] = 2, ["Version"] = p.Format == 3 ? 3 : p.Format == 4 ? 10 : 20,
                ["OriginalTrainerName"] = "Fixture", ["IV_HP"] = 17, ["MetLevel"] = 5,
                ["MetLocation"] = 1, ["CurrentLevel"] = 42,
            }) Set(p, pair.Key, pair.Value);
            var properties = new Dictionary<string, object?>();
            foreach (var name in new[] { "Format", "Generation", "Context", "PID", "EncryptionConstant", "TID16", "SID16",
                "Version", "MetLocation", "MetLevel", "MetDate", "EggLocation", "EggMetDate", "Language", "Gender",
                "Form", "IsShiny", "Checksum", "OriginalTrainerName", "OriginalTrainerGender", "IsEgg", "IV32" })
            {
                var prop = p.GetType().GetProperty(name);
                properties[name] = prop == null ? null : new { type = prop.PropertyType.Name,
                    declared = prop.DeclaringType!.Name, value = prop.GetValue(p)?.ToString() };
            }
            var initial = export.Invoke(null, new object[] { assembly, p, 0, 0, "party" });
            Set(p, "Species", 93); Set(p, "CurrentLevel", 45); Set(p, "Move1", 85);
            Set(p, "EV_HP", 40); Set(p, "HeldItem", 1); Set(p, "Nickname", "Changed");
            var evolved = export.Invoke(null, new object[] { assembly, p, 2, 4, "box" });
            Set(p, "Species", 94);
            var final = export.Invoke(null, new object[] { assembly, p, 3, 2, "box" });
            rows.Add(new { format = p.Format, properties, initial, evolved, final });
        }
        Console.WriteLine(JsonSerializer.Serialize(new { version = assembly.GetName().Version!.ToString(), rows }));
    }
}
