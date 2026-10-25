using PKHeX.Core;

// Negative23D transport inputs only. Never changes supplied fixture bytes.
internal static class TransportForgeries
{
    internal static void Run(string input, string output)
    {
        var bytes = File.ReadAllBytes(input);
        var save = SaveUtil.GetVariantSAV((byte[])bytes.Clone()) ?? throw new Exception("Invalid fixture");
        if (!save.ChecksumsValid || save.Version != GameVersion.X) throw new Exception("Requires retained X fixture");
        Directory.CreateDirectory(output);
        save.Money = save.Money == 1 ? 2u : 1u;
        using (var f = new FileStream(Path.Combine(output, "extra-money"), FileMode.CreateNew)) f.Write(save.Write());
        save = SaveUtil.GetVariantSAV((byte[])bytes.Clone())!;
        var mon = save.GetBoxSlotAtIndex(0, 0);
        if (mon.Species == 0) throw new Exception("Missing target");
        mon.IV_HP ^= 1; mon.RefreshChecksum();
        save.WriteBoxSlot(mon, save.Data.AsSpan(save.GetBoxSlotOffset(0, 0), 232));
        using (var f = new FileStream(Path.Combine(output, "extra-pkm"), FileMode.CreateNew)) f.Write(save.Write());
        Console.WriteLine("PASS two native-valid negative transport artifacts; input untouched");
    }
}
