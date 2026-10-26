using PKHeX.Core;
using System.Text.Json;
using static PokeApp.Parser.NativeWrite;

namespace PokeApp.Parser;

// Byte-only paired plan. Same title only (owner rule: cross-title robbery is
// prohibited). Source: stored PKM in boxes 1..7 or a party member; destination:
// first free slot of boxes 1..7. Party removal uses PKHeX's own compaction and
// never leaves an empty party.
public static class NativeTransfer
{
    private static (int Box, int Slot) Free(SaveFile save)
    {
        for (int b=0;b<7;b++) for (int s=0;s<30;s++)
            if (save.GetBoxSlotAtIndex(b,s).Species==0 && !save.IsBoxSlotOverwriteProtected(b,s)) return (b,s);
        throw new Rejection("UNSAFE_TARGET");
    }

    public static object Plan(ReadOnlySpan<byte> bytes)
    {
        try
        {
            using var doc=JsonDocument.Parse(bytes.ToArray(),new JsonDocumentOptions{MaxDepth=8});
            var r=doc.RootElement;
            Exact(r,["schema_version","source_base64","destination_base64","pair_id","location","box_index","slot_index","target_pid","target_ec"]);
            if(Integer(r,"schema_version")!=1 || !Guid.TryParseExact(Text(r,"pair_id"),"D",out _)) throw new Rejection("INVALID_REQUEST");
            byte[] a=Bytes(r,"source_base64"), b=Bytes(r,"destination_base64");
            var donor=Validate(a); var receiver=Validate(b);
            if(donor.Version!=receiver.Version) throw new Rejection("WRONG_GAME");
            if(TrainerKey(donor)==TrainerKey(receiver)) throw new Rejection("WRONG_TRAINER");
            string location=Text(r,"location");
            int box=Integer(r,"box_index"),slot=Integer(r,"slot_index");
            PKM target;
            if(location=="box") {
                if(box<0||box>6||slot<0||slot>=30) throw new Rejection("UNSAFE_TARGET");
                target=donor.GetBoxSlotAtIndex(box,slot);
            } else if(location=="party") {
                if(box!=-1||slot<0||slot>=donor.PartyCount) throw new Rejection("UNSAFE_TARGET");
                if(donor.PartyCount<2) throw new Rejection("LAST_PARTY_MEMBER");
                target=donor.GetPartySlotAtIndex(slot);
            } else throw new Rejection("INVALID_REQUEST");
            if(!r.GetProperty("target_pid").TryGetUInt32(out uint pid)||!r.GetProperty("target_ec").TryGetUInt32(out uint ec)
                ||target.PID!=pid||target.EncryptionConstant!=ec) throw new Rejection("UNSAFE_TARGET");
            // The 232 stored bytes are the box form: identity, OT, IVs, moves, EXP.
            var pkm=Convert.ToBase64String(location=="box"
                ? donor.Data.AsSpan(donor.GetBoxSlotOffset(box,slot),232).ToArray() : target.EncryptedBoxData);
            var free=Free(receiver);
            object Intent(SaveFile own,byte[] raw,SaveFile peer,byte[] peerRaw,string kind,string loc,int bx,int sl)=>new {
                Game=own.Version.ToString(), ExpectedSha256=Hash(raw),TrainerKey=TrainerKey(own),
                Mutation=new {Kind=kind,PairId=Text(r,"pair_id"),PeerSha256=Hash(peerRaw),PeerTrainerKey=TrainerKey(peer),
                    Location=loc,BoxIndex=bx,SlotIndex=sl,TargetPid=pid,TargetEc=ec,PkmBase64=pkm}
            };
            var origin=Intent(donor,a,receiver,b,"transfer_remove",location,box,slot);
            var destination=Intent(receiver,b,donor,a,"transfer_insert","box",free.Box,free.Slot);
            // Validate both plans now, before permitting either physical side.
            foreach(var pair in new[]{(origin,a),(destination,b)}) {
                var request=JsonSerializer.SerializeToElement(new {SchemaVersion=1,SourceBase64=Convert.ToBase64String(pair.Item2),Intent=pair.Item1},Inspection.Json);
                Execute(request,false);
            }
            return new {SchemaVersion=1,WriterVersion,Status="planned",Error=(string?)null,
                Game=donor.Version.ToString(),TrainerKey=TrainerKey(donor),SourceSha256=Hash(a),OutputSha256=(string?)null,
                OutputBase64=(string?)null,SemanticDiff=new {Source=origin,Destination=destination}};
        }
        catch(Rejection e){return Failure(e.Code);}
        catch(Exception){return Failure("WRITE_PREPARATION_FAILED");}
    }

    internal static object Execute(JsonElement root,bool verify)
    {
        var intent=root.GetProperty("intent"); Exact(intent,["game","expected_sha256","trainer_key","mutation"]);
        var m=intent.GetProperty("mutation");
        Exact(m,["kind","pair_id","peer_sha256","peer_trainer_key","location","box_index","slot_index","target_pid","target_ec","pkm_base64"]);
        string kind=Text(m,"kind"),location=Text(m,"location"); bool remove=kind=="transfer_remove", party=location=="party";
        if(!remove&&kind!="transfer_insert" || !(location=="box"||party&&remove) || !Guid.TryParseExact(Text(m,"pair_id"),"D",out _)
            || !System.Text.RegularExpressions.Regex.IsMatch(Text(m,"peer_sha256"),"^[a-f0-9]{64}$")
            || !System.Text.RegularExpressions.Regex.IsMatch(Text(m,"peer_trainer_key"),"^[a-f0-9]{64}$")) throw new Rejection("INVALID_REQUEST");
        byte[] original=Bytes(root,"source_base64"); var save=Validate(original);
        if(Hash(original)!=Text(intent,"expected_sha256")) throw new Rejection("STALE_SOURCE");
        if(save.Version.ToString()!=Text(intent,"game")) throw new Rejection("WRONG_GAME");
        if(TrainerKey(save)!=Text(intent,"trainer_key") || TrainerKey(save)==Text(m,"peer_trainer_key")) throw new Rejection("WRONG_TRAINER");
        int box=Integer(m,"box_index"),slot=Integer(m,"slot_index");
        if(party ? box!=-1||slot<0||slot>=save.PartyCount
                 : box<0||box>6||slot<0||slot>=30||save.BoxCount<8||save.BoxSlotCount!=30||save.IsBoxSlotOverwriteProtected(box,slot))
            throw new Rejection("UNSAFE_TARGET");
        if(party&&save.PartyCount<2) throw new Rejection("LAST_PARTY_MEMBER");
        byte[] pkm=Convert.FromBase64String(Text(m,"pkm_base64"));
        if(pkm.Length!=232) throw new Rejection("INVALID_REQUEST");
        PKM target=save.Generation==6 ? new PK6((byte[])pkm.Clone()) : new PK7((byte[])pkm.Clone());
        if(!m.GetProperty("target_pid").TryGetUInt32(out uint pid)||!m.GetProperty("target_ec").TryGetUInt32(out uint ec)
            ||target.Species==0||target.IsEgg||target is not G6PKM {Sanity:0}||!target.ChecksumValid
            ||target.PID!=pid||target.EncryptionConstant!=ec) throw new Rejection("UNSAFE_TARGET");
        int collisions=save.BoxData.Concat(save.PartyData).Count(p=>p.Species!=0&&(p.PID==pid||p.EncryptionConstant==ec));
        int offset=party ? save.GetPartyOffset(slot) : save.GetBoxSlotOffset(box,slot);
        if(remove) {
            var current=party ? save.GetPartySlotAtIndex(slot).EncryptedBoxData : save.Data.AsSpan(offset,232).ToArray();
            if(collisions!=1||!current.AsSpan().SequenceEqual(pkm)
                ||target.TID16!=save.TID16||target.SID16!=save.SID16||target.OriginalTrainerName!=save.OT
                ||target.OriginalTrainerGender!=save.Gender||target.Language!=save.Language) throw new Rejection("UNSAFE_TARGET");
        } else if(collisions!=0||Free(save)!=(box,slot)) throw new Rejection("UNSAFE_TARGET");
        var clone=save.Clone();
        if(party) clone.DeletePartySlot(slot); // PKHeX compaction: later members move up, count - 1
        else if(remove) clone.WriteBoxSlot(clone.BlankPKM,clone.Data.AsSpan(offset,232));
        else pkm.CopyTo(clone.Data,offset); // preserve OT, IVs, moves, ability and all PKM bytes
        byte[] expected=clone.Write(),output=verify?Bytes(root,"output_base64"):expected;
        if(original.AsSpan().SequenceEqual(output)||!output.AsSpan().SequenceEqual(expected)) throw new Rejection("UNEXPECTED_DIFF");
        var result=Validate(output);
        if(TrainerKey(result)!=TrainerKey(save)||result.Version!=save.Version) throw new Rejection("VERIFICATION_FAILED");
        int start=offset,length=232;
        if(party) {
            // Exact compaction: earlier members identical, later ones shifted by one,
            // every box identical, and the stolen individual gone from this save.
            var before=save.PartyData; var after=result.PartyData;
            if(after.Count!=before.Count-1||result.PartyCount!=save.PartyCount-1) throw new Rejection("VERIFICATION_FAILED");
            for(int i=0;i<after.Count;i++)
                if(!after[i].EncryptedPartyData.AsSpan().SequenceEqual(before[i<slot?i:i+1].EncryptedPartyData)) throw new Rejection("VERIFICATION_FAILED");
            if(!save.BoxData.Zip(result.BoxData).All(x=>x.First.EncryptedBoxData.AsSpan().SequenceEqual(x.Second.EncryptedBoxData))
                ||result.BoxData.Concat(result.PartyData).Any(p=>p.Species!=0&&(p.PID==pid||p.EncryptionConstant==ec)))
                throw new Rejection("VERIFICATION_FAILED");
            start=save.GetPartyOffset(0); length=save.GetPartyOffset(5)+(save.GetPartyOffset(1)-save.GetPartyOffset(0))-start;
        }
        var block=save.AllBlocks.Where(b=>start>=b.Offset&&start+length<=b.Offset+b.Length).ToArray();
        if(block.Length!=1) throw new Rejection("UNSUPPORTED_FORMAT");
        int checksum=original.Length-0x200+0x14+checked((int)block[0].ID*8)+6;
        int sig=save is SAV7USUM?0x6C000+MemeCrypto.SaveFileSignatureOffset:save is SAV7SM?0x6BA00+MemeCrypto.SaveFileSignatureOffset:-1;
        int lo=party?block[0].Offset:start,hi=party?block[0].Offset+block[0].Length:start+length;
        for(int i=0;i<original.Length;i++) if(original[i]!=output[i]&&!(i>=lo&&i<hi||i==checksum||i==checksum+1||sig>=0&&i>=sig&&i<sig+MemeCrypto.SaveFileSignatureLength)) throw new Rejection("UNEXPECTED_DIFF");
        var diff=JsonSerializer.Deserialize<Dictionary<string,object>>(m.GetRawText())!;
        diff["preserved_unrelated"]=true;diff["checksums_valid"]=true;diff["signature_valid"]=true;
        return new {SchemaVersion=1,WriterVersion,Status=verify?"verified":"prepared",Error=(string?)null,
            Game=save.Version.ToString(),TrainerKey=TrainerKey(save),SourceSha256=Hash(original),OutputSha256=Hash(output),
            OutputBase64=verify?null:Convert.ToBase64String(output),SemanticDiff=diff};
    }
}
