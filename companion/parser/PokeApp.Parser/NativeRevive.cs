using PKHeX.Core;
using System.Text.Json;
using static PokeApp.Parser.NativeWrite;

namespace PokeApp.Parser;

// Existing legacy contract: Caja8 -> first free slot in Cajas1..7, preserving
// the complete Pokemon. No heal, party insertion, stats, money or Pokedex edits.
internal static class NativeRevive
{
    internal static object Execute(JsonElement root, bool verify)
    {
        var intent = root.GetProperty("intent");
        Exact(intent, ["game", "expected_sha256", "trainer_key", "mutation"]);
        var m = intent.GetProperty("mutation");
        Exact(m, ["kind", "location", "box_index", "slot_index", "target_pid", "target_ec",
                  "destination_box_index", "destination_slot_index"]);
        if (Text(m, "kind") != "revive" || Text(m, "location") != "box" || Integer(m, "box_index") != 7)
            throw new Rejection("UNSAFE_TARGET");
        var original = Bytes(root, "source_base64");
        var source = Validate(original);
        var game = Text(intent, "game");
        var trainer = Text(intent, "trainer_key");
        if (Hash(original) != Text(intent, "expected_sha256")) throw new Rejection("STALE_SOURCE");
        if (game != source.Version.ToString()) throw new Rejection("WRONG_GAME");
        if (trainer != TrainerKey(source)) throw new Rejection("WRONG_TRAINER");
        int slot = Integer(m, "slot_index"), db = Integer(m, "destination_box_index"), ds = Integer(m, "destination_slot_index");
        if (source.BoxCount < 8 || source.BoxSlotCount != 30 || slot < 0 || slot >= 30
            || db < 0 || db > 6 || ds < 0 || ds >= 30
            || source.IsBoxSlotOverwriteProtected(7, slot) || source.IsBoxSlotOverwriteProtected(db, ds))
            throw new Rejection("UNSAFE_TARGET");
        var before = source.GetBoxSlotAtIndex(7, slot);
        if (!m.GetProperty("target_pid").TryGetUInt32(out uint pid)
            || !m.GetProperty("target_ec").TryGetUInt32(out uint ec)) throw new Rejection("INVALID_REQUEST");
        if (before.Species == 0 || before.IsEgg || before is not G6PKM { Sanity: 0 }
            || !before.ChecksumValid || before.PID != pid || before.EncryptionConstant != ec
            || before.TID16 != source.TID16 || before.SID16 != source.SID16
            || before.OriginalTrainerName != source.OT || before.OriginalTrainerGender != source.Gender
            || before.Language != source.Language)
            throw new Rejection("UNSAFE_TARGET");
        int collisions = 0;
        foreach (var p in source.BoxData.Concat(source.PartyData))
            if (p.Species != 0 && (p.PID == pid || p.EncryptionConstant == ec)) collisions++;
        if (collisions != 1) throw new Rejection("UNSAFE_TARGET");
        (int box, int index) first = (-1, -1);
        for (int b = 0; b < 7 && first.box < 0; b++)
            for (int s = 0; s < 30; s++)
                if (source.GetBoxSlotAtIndex(b,s).Species == 0) { first = (b,s); break; }
        if (first != (db,ds)) throw new Rejection("UNSAFE_TARGET");

        var clone = source.Clone();
        int srcOffset = source.GetBoxSlotOffset(7,slot), dstOffset = source.GetBoxSlotOffset(db,ds);
        // Raw stored-PKM copy is deliberately free of import handlers, healing,
        // records, trade metadata and Pokedex side effects.
        source.Data.AsSpan(srcOffset,232).CopyTo(clone.Data.AsSpan(dstOffset,232));
        clone.WriteBoxSlot(clone.BlankPKM, clone.Data.AsSpan(srcOffset,232));
        var expected = clone.Write();
        byte[] output = verify ? Bytes(root,"output_base64") : expected;
        if (original.Length != output.Length || original.AsSpan().SequenceEqual(output)
            || !output.AsSpan().SequenceEqual(expected)) throw new Rejection("UNEXPECTED_DIFF");
        var result = Validate(output);
        if (result.Version.ToString() != game || TrainerKey(result) != trainer
            || result.GetBoxSlotAtIndex(7,slot).Species != 0
            || !result.Data.AsSpan(dstOffset,232).SequenceEqual(source.Data.AsSpan(srcOffset,232)))
            throw new Rejection("VERIFICATION_FAILED");
        // Independently constrain even the serializer: only two slots, their
        // block checksums and the existing Gen7 native signature may differ.
        var allowedChecksums = new HashSet<int>();
        foreach (var offset in new[]{srcOffset,dstOffset})
        {
            var blocks = source.AllBlocks.Where(b=>offset>=b.Offset && offset+232<=b.Offset+b.Length).ToArray();
            if(blocks.Length!=1) throw new Rejection("UNSUPPORTED_FORMAT");
            int c = original.Length-0x200+0x14+checked((int)blocks[0].ID*8)+6;
            allowedChecksums.Add(c); allowedChecksums.Add(c+1);
        }
        int sig=source is SAV7USUM ? 0x6C000+MemeCrypto.SaveFileSignatureOffset
               : source is SAV7SM ? 0x6BA00+MemeCrypto.SaveFileSignatureOffset : -1;
        for(int i=0;i<original.Length;i++)
            if(original[i]!=output[i] && !(i>=srcOffset && i<srcOffset+232
                || i>=dstOffset && i<dstOffset+232 || allowedChecksums.Contains(i)
                || sig>=0 && i>=sig && i<sig+MemeCrypto.SaveFileSignatureLength))
                throw new Rejection("UNEXPECTED_DIFF");
        return new {
            SchemaVersion=1, WriterVersion, Status=verify?"verified":"prepared", Error=(string?)null,
            Game=game, TrainerKey=trainer, SourceSha256=Hash(original), OutputSha256=Hash(output),
            OutputBase64=verify?null:Convert.ToBase64String(output),
            SemanticDiff=new {Kind="revive",Location="box",BoxIndex=7,SlotIndex=slot,
                TargetPid=pid,TargetEc=ec,DestinationBoxIndex=db,DestinationSlotIndex=ds,
                PreservedUnrelated=true,ChecksumsValid=true,SignatureValid=true}
        };
    }
}
