using System.Text.Json;
using PokeApp.Parser;

// Bytes only. No caller path, flags selecting writes, UI or network access.
if (args.Length != 0)
{
    Console.WriteLine(JsonSerializer.Serialize(Inspection.Failure("UNSUPPORTED_VERSION"), Inspection.Json));
    return 2;
}
using var input = Console.OpenStandardInput();
using var snapshot = new MemoryStream();
var buffer = new byte[81920];
while (true)
{
    int count = input.Read(buffer);
    if (count == 0) break;
    if (snapshot.Length + count > Inspection.MaxBytes)
    {
        Console.WriteLine(JsonSerializer.Serialize(Inspection.Failure("UNSUPPORTED_VERSION"), Inspection.Json));
        return 2;
    }
    snapshot.Write(buffer, 0, count);
}
Console.WriteLine(JsonSerializer.Serialize(Inspection.Inspect(snapshot.ToArray()), Inspection.Json));
return 0;
