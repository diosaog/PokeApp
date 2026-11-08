using PKHeX.Core;
using System.Text.Json;
using static PokeApp.Parser.NativeWrite;

namespace PokeApp.Parser;

// Read-only facts for the administrator's save audit (server side only): the
// whole bag with each object's pouch, and every Pokémon's current friendship.
// Nothing is judged and no byte is written here; randomized content is reported
// exactly as it is, and legality APIs are never consulted.
public static class NativeAudit
{
    private static readonly string[] Games = ["X", "Y", "OR", "AS", "SN", "MN", "US", "UM"];

    public static object Snapshot(ReadOnlySpan<byte> request)
    {
        try
        {
            if (request.Length is 0 or > MaxRequestBytes) throw new Rejection("INVALID_REQUEST");
            using var document = JsonDocument.Parse(request.ToArray(), new JsonDocumentOptions { MaxDepth = 4 });
            var root = document.RootElement;
            Exact(root, ["schema_version", "source_base64"]);
            if (Integer(root, "schema_version") != 1) throw new Rejection("INVALID_REQUEST");
            var bytes = Bytes(root, "source_base64");
            var save = Validate(bytes);
            if (!Games.Contains(save.Version.ToString(), StringComparer.Ordinal))
                throw new Rejection("UNSUPPORTED_FORMAT");
            var pouches = save.Inventory
                .Select(pouch => new
                {
                    Type = pouch.Type.ToString(),
                    Items = pouch.Items.Where(item => item.Index != 0 && item.Count > 0)
                        .Select(item => new { Id = item.Index, item.Count }).ToArray(),
                })
                .Where(pouch => pouch.Items.Length > 0)
                .ToArray();
            var pokemon = save.PartyData.Concat(save.BoxData)
                .Where(p => p.Species != 0 && !p.IsEgg)
                .Select(p => new { Pid = p.PID, Ec = p.EncryptionConstant, Friendship = (int)p.CurrentFriendship })
                .ToArray();
            return new
            {
                SchemaVersion = 1, WriterVersion, Status = "inspected", Error = (string?)null,
                Game = save.Version.ToString(), TrainerKey = NativeWrite.TrainerKey(save),
                SourceSha256 = Hash(bytes), OutputSha256 = (string?)null, OutputBase64 = (string?)null,
                SemanticDiff = new { Pouches = pouches, Pokemon = pokemon },
            };
        }
        catch (Rejection e) { return Failure(e.Code); }
        catch (JsonException) { return Failure("INVALID_REQUEST"); }
        catch (FormatException) { return Failure("INVALID_REQUEST"); }
        catch (OverflowException) { return Failure("INVALID_REQUEST"); }
        catch (Exception) { return Failure("AUDIT_SNAPSHOT_FAILED"); }
    }
}
