using System.Text.Json;
using PokeApp.Parser;

// Zero args preserves the existing read-only byte protocol exactly. Explicit
// write preparation/verification accepts bytes/intent only: never a path, file
// write, network request or implicit permission to replace a local save.
if (args.Length == 1 && args[0] is "--prepare-write" or "--verify-write" or "--plan-transfer")
{
    using var writeInput = Console.OpenStandardInput();
    using var writeSnapshot = new MemoryStream();
    var writeBuffer = new byte[81920];
    while (true)
    {
        int count = writeInput.Read(writeBuffer);
        if (count == 0) break;
        if (writeSnapshot.Length + count > NativeWrite.MaxRequestBytes)
        {
            Console.WriteLine(JsonSerializer.Serialize(NativeWrite.Failure("INVALID_REQUEST"), Inspection.Json));
            return 2;
        }
        writeSnapshot.Write(writeBuffer, 0, count);
    }
    Console.WriteLine(JsonSerializer.Serialize(args[0] == "--plan-transfer" ? NativeTransfer.Plan(writeSnapshot.ToArray()) : NativeWrite.Execute(writeSnapshot.ToArray(), args[0] == "--verify-write"), Inspection.Json));
    return 0;
}
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
