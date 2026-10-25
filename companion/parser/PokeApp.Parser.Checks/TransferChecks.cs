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
                PairId=Guid.NewGuid().ToString(),BoxIndex=0,SlotIndex=0,TargetPid=target.PID,TargetEc=target.EncryptionConstant};
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
                ["pair_id"]=Guid.NewGuid().ToString(),["box_index"]=0,["slot_index"]=0,["target_pid"]=target.PID,["target_ec"]=target.EncryptionConstant };
            var plan=Plan(request);Check(plan["status"]!.GetValue<string>()=="planned",game+" plan "+plan["error"]);
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
                if(side=="source")Check(after.BoxData.Concat(after.PartyData).All(p=>p.Species==0||p.PID!=target.PID&&p.EncryptionConstant!=target.EncryptionConstant),"removed exactly");
                else Check(after.Data.AsSpan(after.GetBoxSlotOffset(0,0),232).SequenceEqual(donor.Data.AsSpan(donor.GetBoxSlotOffset(0,0),232)),"exact PKM including OT");
                r["output_base64"]=Convert.ToBase64String(output);Check(Apply(r,true)["status"]!.GetValue<string>()=="verified","verification");
                after.Money=after.Money==1?2u:1u;r["output_base64"]=Convert.ToBase64String(after.Write());Check(Apply(r,true)["status"]!.GetValue<string>()=="rejected","unrelated money denied");
                r.Remove("output_base64");var wrong=r.DeepClone();wrong["intent"]!["mutation"]!["target_pid"]=1;
                Check(Apply(wrong)["status"]!.GetValue<string>()=="rejected","wrong Pokemon");
                wrong=r.DeepClone();wrong["intent"]!["expected_sha256"]=new string('0',64);Check(Apply(wrong)["status"]!.GetValue<string>()=="rejected","stale");
                wrong=r.DeepClone();wrong["intent"]!["mutation"]!["box_index"]=7;Check(Apply(wrong)["status"]!.GetValue<string>()=="rejected","dead box denied");
                File.WriteAllBytes(Path.Combine(dir,side+"-result"),output);File.WriteAllText(Path.Combine(dir,side+"-intent.json"),intent.ToJsonString());
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
