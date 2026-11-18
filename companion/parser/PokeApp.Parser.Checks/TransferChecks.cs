using PKHeX.Core;
using PokeApp.Parser;
using System.Text.Json;
using System.Text.Json.Nodes;

internal static class TransferChecks
{
    public static void Compatibility(string root)
    {
        foreach(var game in new[]{"X","Y","OR","AS","SN","MN","US","UM"})
        {
            var source=File.ReadAllBytes(Path.Combine(root,game,"expected"));
            var peer=File.ReadAllBytes(Path.Combine(root,game=="X"?"Y":"X","expected"));
            var target=SaveUtil.GetVariantSAV((byte[])source.Clone())!.GetBoxSlotAtIndex(0,0);
            var request=new {SchemaVersion=1,SourceBase64=Convert.ToBase64String(source),DestinationBase64=Convert.ToBase64String(peer),
                PairId=Guid.NewGuid().ToString(),Location="box",BoxIndex=0,SlotIndex=0,TargetPid=target.PID,TargetEc=target.EncryptionConstant};
            var result=JsonSerializer.SerializeToNode(NativeTransfer.Plan(JsonSerializer.SerializeToUtf8Bytes(request,Inspection.Json)),Inspection.Json)!;
            if(result["status"]!.GetValue<string>()!="rejected"||result["error"]!.GetValue<string>()!="WRONG_GAME") throw new Exception("cross-title unexpectedly admitted: "+game);
        }
        Console.WriteLine("PASS 8 cross-title rejections; no cross-title certification");
    }

    public static void Run(string fixtureRoot,string outputRoot)
    {
        int checks=0;
        void Check(bool ok,string label){if(!ok)throw new Exception(label);checks++;}
        JsonNode Plan(JsonNode request)=>JsonSerializer.SerializeToNode(NativeTransfer.Plan(JsonSerializer.SerializeToUtf8Bytes(request)),Inspection.Json)!;
        JsonNode Apply(JsonNode r,bool verify=false)=>JsonSerializer.SerializeToNode(NativeWrite.Execute(JsonSerializer.SerializeToUtf8Bytes(r),verify),Inspection.Json)!;
        int Bag(SaveFile save,int item)=>item==0?0:save.Inventory.SelectMany(p=>p.Items).Where(i=>i.Index==item).Sum(i=>i.Count);
        byte[] Stripped(PKM pkm){var copy=pkm.Clone();if(copy.HeldItem!=0){copy.HeldItem=0;copy.RefreshChecksum();}return copy.EncryptedBoxData;}
        var games=new List<object>();
        foreach(var game in new[]{"X","Y","OR","AS","SN","MN","US","UM"})
        {
            var path=Path.Combine(fixtureRoot,game,"expected");
            byte[] source=File.ReadAllBytes(path);string originalHash=NativeWrite.Hash(source);
            var donor=SaveUtil.GetVariantSAV((byte[])source.Clone())!;
            var target=donor.GetBoxSlotAtIndex(0,0);
            var receiver=donor.Clone();receiver.OT="Receiver";receiver.TID16^=0x1234;receiver.SID16^=0x4321;
            for(int b=0;b<receiver.BoxCount;b++)for(int s=0;s<30;s++)receiver.WriteBoxSlot(receiver.BlankPKM,receiver.Data.AsSpan(receiver.GetBoxSlotOffset(b,s),232));
            receiver.PartyData=[];
            byte[] destination=receiver.Write();
            var request=new JsonObject { ["schema_version"]=1,["source_base64"]=Convert.ToBase64String(source),["destination_base64"]=Convert.ToBase64String(destination),
                ["pair_id"]=Guid.NewGuid().ToString(),["location"]="box",["box_index"]=0,["slot_index"]=0,["target_pid"]=target.PID,["target_ec"]=target.EncryptionConstant };
            var plan=Plan(request);Check(plan["status"]!.GetValue<string>()=="planned",game+" plan "+plan["error"]);
            // 2026-11-17: the held item stays with the victim (both plans carry it).
            int held=target.HeldItem;
            foreach(var side in new[]{"source","destination"})
                Check(held==0 ? plan["semantic_diff"]![side]!["mutation"]!["held_item"] is null
                              : plan["semantic_diff"]![side]!["mutation"]!["held_item"]!.GetValue<int>()==held,game+" "+side+" plan held item");
            var dir=Path.Combine(outputRoot,game);Directory.CreateDirectory(dir);
            File.WriteAllBytes(Path.Combine(dir,"source"),source);File.WriteAllBytes(Path.Combine(dir,"destination"),destination);
            foreach(var side in new[]{"source","destination"})
            {
                byte[] input=side=="source"?source:destination;
                var intent=plan["semantic_diff"]![side]!.DeepClone();
                var r=new JsonObject { ["schema_version"]=1,["source_base64"]=Convert.ToBase64String(input),["intent"]=intent };
                var result=Apply(r);Check(result["status"]!.GetValue<string>()=="prepared",game+side);
                byte[] output=Convert.FromBase64String(result["output_base64"]!.GetValue<string>());
                var after=SaveUtil.GetVariantSAV((byte[])output.Clone())!;
                Check(after.ChecksumsValid,game+side+" checksum");
                if(side=="source"){
                    Check(after.BoxData.Concat(after.PartyData).All(p=>p.Species==0||p.PID!=target.PID&&p.EncryptionConstant!=target.EncryptionConstant),"removed exactly");
                    Check(Bag(after,held)==Bag(donor,held)+(held!=0&&NativeTransfer.BagCanTake(donor,held)?1:0),game+" held item back in the victim bag");
                } else {
                    Check(after.Data.AsSpan(after.GetBoxSlotOffset(0,0),232).SequenceEqual(Stripped(target)),"exact PKM including OT, without its held item");
                    Check(after.GetBoxSlotAtIndex(0,0).HeldItem==0&&after.GetBoxSlotAtIndex(0,0).ChecksumValid,game+" robber gets no item");
                    Check(Bag(after,held)==Bag(receiver,held),game+" robber bag unchanged");
                }
                r["output_base64"]=Convert.ToBase64String(output);Check(Apply(r,true)["status"]!.GetValue<string>()=="verified","verification");
                after.Money=after.Money==1?2u:1u;r["output_base64"]=Convert.ToBase64String(after.Write());Check(Apply(r,true)["status"]!.GetValue<string>()=="rejected","unrelated money denied");
                r.Remove("output_base64");var wrong=r.DeepClone();wrong["intent"]!["mutation"]!["target_pid"]=1;
                Check(Apply(wrong)["status"]!.GetValue<string>()=="rejected","wrong Pokemon");
                wrong=r.DeepClone();wrong["intent"]!["expected_sha256"]=new string('0',64);Check(Apply(wrong)["status"]!.GetValue<string>()=="rejected","stale");
                wrong=r.DeepClone();wrong["intent"]!["mutation"]!["box_index"]=7;Check(Apply(wrong)["status"]!.GetValue<string>()=="rejected","dead box denied");
                if(held!=0){
                    wrong=r.DeepClone();wrong["intent"]!["mutation"]!["held_item"]=held==1?2:1;
                    Check(Apply(wrong)["status"]!.GetValue<string>()=="rejected",game+side+" forged held item denied");
                    // A plan made before the rule (no held_item) applies exactly as before.
                    var legacy=r.DeepClone();legacy["intent"]!["mutation"]!.AsObject().Remove("held_item");
                    var old=Apply(legacy);Check(old["status"]!.GetValue<string>()=="prepared",game+side+" pre-rule plan still applies");
                    var oldAfter=SaveUtil.GetVariantSAV(Convert.FromBase64String(old["output_base64"]!.GetValue<string>()))!;
                    if(side=="destination")Check(oldAfter.Data.AsSpan(oldAfter.GetBoxSlotOffset(0,0),232).SequenceEqual(donor.Data.AsSpan(donor.GetBoxSlotOffset(0,0),232)),"pre-rule exact PKM");
                    else Check(Bag(oldAfter,held)==Bag(donor,held),"pre-rule removal leaves the bag");
                }
                File.WriteAllBytes(Path.Combine(dir,side+"-result"),output);File.WriteAllText(Path.Combine(dir,side+"-intent.json"),intent.ToJsonString());
            }
            if(held!=0){
                // A Pokemon without an item keeps the earlier plan shape exactly.
                var plain=donor.Clone();var bare=target.Clone();bare.HeldItem=0;bare.RefreshChecksum();
                plain.SetBoxSlotAtIndex(bare,0,0);
                var bareRequest=request.DeepClone();bareRequest["source_base64"]=Convert.ToBase64String(plain.Write());
                var barePlan=Plan(bareRequest);Check(barePlan["status"]!.GetValue<string>()=="planned",game+" item-less plan");
                Check(barePlan["semantic_diff"]!["source"]!["mutation"]!["held_item"] is null&&barePlan["semantic_diff"]!["destination"]!["mutation"]!["held_item"] is null,game+" item-less plan has no held_item");
            }
            var bad=request.DeepClone();bad["destination_base64"]=bad["source_base64"]!.DeepClone();Check(Plan(bad)["status"]!.GetValue<string>()=="rejected","same trainer");
            var clone=receiver.Clone();clone.WriteBoxSlot(target,clone.Data.AsSpan(clone.GetBoxSlotOffset(0,0),232));
            bad=request.DeepClone();bad["destination_base64"]=Convert.ToBase64String(clone.Write());Check(Plan(bad)["status"]!.GetValue<string>()=="rejected","duplicate target");
            clone=receiver.Clone();
            for(int b=0;b<7;b++)for(int s=0;s<30;s++){var filler=target.Clone();filler.PID+=(uint)(1+b*30+s);filler.EncryptionConstant+=(uint)(1+b*30+s);filler.RefreshChecksum();clone.WriteBoxSlot(filler,clone.Data.AsSpan(clone.GetBoxSlotOffset(b,s),232));}
            bad=request.DeepClone();bad["destination_base64"]=Convert.ToBase64String(clone.Write());Check(Plan(bad)["status"]!.GetValue<string>()=="rejected","no space");
            Check(NativeWrite.Hash(File.ReadAllBytes(path))==originalHash,"fixture unchanged");
            games.Add(new{Game=game,SourceSha256=originalHash,DestinationSha256=NativeWrite.Hash(destination),Status="PASS"});
        }
        File.WriteAllText(Path.Combine(outputRoot,"native-evidence.json"),JsonSerializer.Serialize(new{Status="PASS",Checks=checks,Games=games},Inspection.Json));
        Console.WriteLine($"PASS {checks} checks across eight same-title boxed transfers");
    }
}
