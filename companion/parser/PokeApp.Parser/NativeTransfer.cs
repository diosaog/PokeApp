using PKHeX.Core;
using System.Text.Json;
using static PokeApp.Parser.NativeWrite;

namespace PokeApp.Parser;

// Byte-only paired plan. Same title only (owner rule: cross-title robbery is
// prohibited). Source: stored PKM in boxes 1..7 or a party member; destination:
// first free slot of boxes 1..6, never the official dead box (Caja 7): a stolen
// Pokémon stored there would count as a death. Party removal uses PKHeX's own
// compaction and never leaves an empty party.
//
// Owner rule of 2026-11-17: a robbery takes the Pokémon, never its held item.
// When the Pokémon holds an item, both plans carry `held_item`: the robber
// receives the same individual with no held item (checksum recomputed;
// identity, OT, IVs, moves and all other bytes unchanged), and the removal adds
// one unit of it to the victim's bag whenever that bag can store it. A Gen 7
// held Z-Crystal cannot go to the bag: the victim keeps its key-item version,
// so nothing is added. The decision comes from the same pinned bytes on every
// side. Plans without `held_item` keep the earlier byte-exact behaviour, so
// journals and in-flight plans verify as before; an older writer refuses the key.
public static class NativeTransfer
{
    private static (int Box, int Slot) Free(SaveFile save)
    {
        for (int b=0;b<6;b++) for (int s=0;s<30;s++)
            if (save.GetBoxSlotAtIndex(b,s).Species==0 && !save.IsBoxSlotOverwriteProtected(b,s)) return (b,s);
        throw new Rejection("UNSAFE_TARGET");
    }

    // One unit of `item` can be added to this save's bag (existing stack below
    // its maximum, or an empty slot in the only pouch that holds it).
    public static bool BagCanTake(SaveFile save,int item)
    {
        try
        {
            var pouches=save.Inventory;
            var (index,slot)=NativeItems.Find(pouches,(ushort)item);
            var pouch=pouches[index];
            return slot is not null ? slot.Count<pouch.MaxCount : pouch.Items.Any(i=>i.Index==0);
        }
        catch(Rejection){return false;}
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
            // The held item never goes to the robber.
            int held=target.HeldItem;
            bool keep=held>0;
            object Intent(SaveFile own,byte[] raw,SaveFile peer,byte[] peerRaw,string kind,string loc,int bx,int sl)
            {
                var mutation=new Dictionary<string,object>{
                    ["kind"]=kind,["pair_id"]=Text(r,"pair_id"),["peer_sha256"]=Hash(peerRaw),["peer_trainer_key"]=TrainerKey(peer),
                    ["location"]=loc,["box_index"]=bx,["slot_index"]=sl,["target_pid"]=pid,["target_ec"]=ec,["pkm_base64"]=pkm};
                if(keep) mutation["held_item"]=held;
                return new {Game=own.Version.ToString(),ExpectedSha256=Hash(raw),TrainerKey=TrainerKey(own),Mutation=mutation};
            }
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
        bool item=m.TryGetProperty("held_item",out _);
        Exact(m,item
            ? ["kind","pair_id","peer_sha256","peer_trainer_key","location","box_index","slot_index","target_pid","target_ec","pkm_base64","held_item"]
            : ["kind","pair_id","peer_sha256","peer_trainer_key","location","box_index","slot_index","target_pid","target_ec","pkm_base64"]);
        string kind=Text(m,"kind"),location=Text(m,"location"); bool remove=kind=="transfer_remove", party=location=="party";
        if(!remove&&kind!="transfer_insert" || !(location=="box"||party&&remove) || !Guid.TryParseExact(Text(m,"pair_id"),"D",out _)
            || !System.Text.RegularExpressions.Regex.IsMatch(Text(m,"peer_sha256"),"^[a-f0-9]{64}$")
            || !System.Text.RegularExpressions.Regex.IsMatch(Text(m,"peer_trainer_key"),"^[a-f0-9]{64}$")) throw new Rejection("INVALID_REQUEST");
        int held=item?Integer(m,"held_item"):0;
        if(item&&(held<1||held>ushort.MaxValue)) throw new Rejection("INVALID_REQUEST");
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
        if(item&&target.HeldItem!=held) throw new Rejection("UNSAFE_TARGET");
        int collisions=save.BoxData.Concat(save.PartyData).Count(p=>p.Species!=0&&(p.PID==pid||p.EncryptionConstant==ec));
        int offset=party ? save.GetPartyOffset(slot) : save.GetBoxSlotOffset(box,slot);
        if(remove) {
            var current=party ? save.GetPartySlotAtIndex(slot).EncryptedBoxData : save.Data.AsSpan(offset,232).ToArray();
            if(collisions!=1||!current.AsSpan().SequenceEqual(pkm)
                ||target.TID16!=save.TID16||target.SID16!=save.SID16||target.OriginalTrainerName!=save.OT
                ||target.OriginalTrainerGender!=save.Gender||target.Language!=save.Language) throw new Rejection("UNSAFE_TARGET");
        } else if(collisions!=0||Free(save)!=(box,slot)) throw new Rejection("UNSAFE_TARGET");
        // The robber's copy without its held item: same individual, item 0.
        byte[] inserted=pkm;
        if(!remove&&item) {
            var stripped=target.Clone(); stripped.HeldItem=0; stripped.RefreshChecksum();
            inserted=stripped.EncryptedBoxData;
            if(inserted.Length!=232) throw new Rejection("UNSUPPORTED_FORMAT");
        }
        var clone=save.Clone();
        if(party) clone.DeletePartySlot(slot); // PKHeX compaction: later members move up, count - 1
        else if(remove) clone.WriteBoxSlot(clone.BlankPKM,clone.Data.AsSpan(offset,232));
        else inserted.CopyTo(clone.Data,offset); // preserve OT, IVs, moves, ability and all other PKM bytes
        int bagIndex=-1;
        int bagCount=0;
        bool bagged=remove&&item&&BagCanTake(save,held);
        if(bagged) {
            // The held item goes back to the victim's bag: one more unit of it.
            var pouches=clone.Inventory;
            var (index,existing)=NativeItems.Find(pouches,(ushort)held);
            var pouch=pouches[index];
            bagIndex=index; bagCount=existing?.Count??0;
            if(existing is null) {
                var empty=pouch.Items.FirstOrDefault(i=>i.Index==0) ?? throw new Rejection("INVENTORY_FULL");
                empty.Index=held; empty.SetNewDetails(1); empty.Count=1;
            } else {
                if(existing.Count>=pouch.MaxCount) throw new Rejection("INVENTORY_FULL");
                existing.Count+=1;
            }
            clone.Inventory=pouches;
        }
        byte[] expected=clone.Write();
        NativeTraining.NormalizeGeneratedSignature(expected,save);
        byte[] output=verify?Bytes(root,"output_base64"):expected;
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
        if(!remove&&item) {
            var received=result.GetBoxSlotAtIndex(box,slot);
            if(received.PID!=pid||received.EncryptionConstant!=ec||received.HeldItem!=0||received.Species!=target.Species
                ||!received.ChecksumValid) throw new Rejection("VERIFICATION_FAILED");
        }
        if(remove&&item&&!bagged) {
            // Nothing else changes when the item cannot go to the bag.
            var before=save.Inventory; var after=result.Inventory;
            if(after.Count!=before.Count||Enumerable.Range(0,before.Count).Any(p=>!before[p].Items.Where(i=>i.Index!=0).Select(i=>(i.Index,i.Count))
                .SequenceEqual(after[p].Items.Where(i=>i.Index!=0).Select(i=>(i.Index,i.Count))))) throw new Rejection("UNEXPECTED_DIFF");
        }
        if(bagged) {
            // Exactly one more unit of the held item; every other bag entry identical.
            var before=save.Inventory; var after=result.Inventory;
            if(after.Count!=before.Count) throw new Rejection("VERIFICATION_FAILED");
            for(int p=0;p<before.Count;p++) {
                var old=before[p].Items.Where(i=>i.Index!=0&&!(p==bagIndex&&i.Index==held)).Select(i=>(i.Index,i.Count));
                var now=after[p].Items.Where(i=>i.Index!=0&&!(p==bagIndex&&i.Index==held)).Select(i=>(i.Index,i.Count));
                if(!old.SequenceEqual(now)) throw new Rejection("UNEXPECTED_DIFF");
            }
            var added=after[bagIndex].Items.Where(i=>i.Index==held).ToArray();
            if(added.Length!=1||added[0].Count!=bagCount+1||result.Money!=save.Money) throw new Rejection("VERIFICATION_FAILED");
        }
        var block=save.AllBlocks.Where(b=>start>=b.Offset&&start+length<=b.Offset+b.Length).ToArray();
        if(block.Length!=1) throw new Rejection("UNSUPPORTED_FORMAT");
        int table=original.Length-0x200;
        int Checksum(int id)=>table+0x14+checked(id*8)+6;
        int checksum=Checksum(checked((int)block[0].ID));
        int sig=save is SAV7USUM?0x6C000+MemeCrypto.SaveFileSignatureOffset:save is SAV7SM?0x6BA00+MemeCrypto.SaveFileSignatureOffset:-1;
        int lo=party?block[0].Offset:start,hi=party?block[0].Offset+block[0].Length:start+length;
        bool Signature(int i)=>sig>=0&&i>=sig&&i<sig+MemeCrypto.SaveFileSignatureLength;
        bool Allowed(int i)=>i>=lo&&i<hi||i==checksum||i==checksum+1||Signature(i);
        int bagLo=-1,bagHi=-1,bagSum=-1;
        if(bagged) {
            // The second changed block must be the bag, the only one that may also change.
            var extra=Enumerable.Range(0,table).Where(i=>original[i]!=output[i]&&!Allowed(i)).ToArray();
            if(extra.Length==0) throw new Rejection("UNEXPECTED_DIFF");
            var bag=save.AllBlocks.Where(b=>extra[0]>=b.Offset&&extra[0]<b.Offset+b.Length).ToArray();
            if(bag.Length!=1||bag[0].Offset==block[0].Offset) throw new Rejection("UNSUPPORTED_FORMAT");
            bagLo=bag[0].Offset; bagHi=bag[0].Offset+bag[0].Length; bagSum=Checksum(checked((int)bag[0].ID));
        }
        for(int i=0;i<original.Length;i++)
            if(original[i]!=output[i]&&!Allowed(i)&&!(i>=bagLo&&i<bagHi||i==bagSum||i==bagSum+1)) throw new Rejection("UNEXPECTED_DIFF");
        var diff=JsonSerializer.Deserialize<Dictionary<string,object>>(m.GetRawText())!;
        diff["preserved_unrelated"]=true;diff["checksums_valid"]=true;diff["signature_valid"]=true;
        return new {SchemaVersion=1,WriterVersion,Status=verify?"verified":"prepared",Error=(string?)null,
            Game=save.Version.ToString(),TrainerKey=TrainerKey(save),SourceSha256=Hash(original),OutputSha256=Hash(output),
            OutputBase64=verify?null:Convert.ToBase64String(output),SemanticDiff=diff};
    }
}
