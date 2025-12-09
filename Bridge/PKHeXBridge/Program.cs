// Program.cs ? Bridge Gen4 con getter seguro + posiciones + OT + flags (--mode/--box) (v7j)
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.Json;

namespace PKHeXBridgeApp
{
    static class Ref
    {
        public static object? Call(object? target, string name, params object?[] args)
        {
            if (target is null) return null;
            var t = target as Type ?? target.GetType();
            var flags = BindingFlags.Public | BindingFlags.NonPublic |
                        ((target is Type) ? BindingFlags.Static : BindingFlags.Instance);

            foreach (var m in t.GetMember(name, MemberTypes.Method, flags))
            {
                var mi = (MethodInfo)m;
                var ps = mi.GetParameters();
                if (ps.Length != args.Length) continue;
                try
                {
                    // Intentar invocar directamente
                    return mi.Invoke(target is Type ? null : target, args);
                }
                catch
                {
                    // Reintento con conversi?n de tipos num?ricos (int -> short/ushort/byte, etc.)
                    try
                    {
                        var conv = new object?[args.Length];
                        for (int i = 0; i < args.Length; i++)
                        {
                            var pt = ps[i].ParameterType;
                            var val = args[i];
                            if (pt.IsByRef) pt = pt.GetElementType()!;
                            if (val == null) { conv[i] = null; continue; }

                            Type nt = Nullable.GetUnderlyingType(pt) ?? pt;
                            try
                            {
                                if (nt.IsEnum)
                                {
                                    conv[i] = Enum.ToObject(nt, Convert.ChangeType(val, Enum.GetUnderlyingType(nt))!);
                                }
                                else if (nt == typeof(byte))
                                    conv[i] = Convert.ToByte(val);
                                else if (nt == typeof(sbyte))
                                    conv[i] = Convert.ToSByte(val);
                                else if (nt == typeof(short))
                                    conv[i] = Convert.ToInt16(val);
                                else if (nt == typeof(ushort))
                                    conv[i] = Convert.ToUInt16(val);
                                else if (nt == typeof(int))
                                    conv[i] = Convert.ToInt32(val);
                                else if (nt == typeof(uint))
                                    conv[i] = Convert.ToUInt32(val);
                                else if (nt == typeof(long))
                                    conv[i] = Convert.ToInt64(val);
                                else if (nt == typeof(ulong))
                                    conv[i] = Convert.ToUInt64(val);
                                else
                                    conv[i] = Convert.ChangeType(val, nt);
                            }
                            catch { conv[i] = val; }
                        }
                        return mi.Invoke(target is Type ? null : target, conv);
                    }
                    catch { /* probar siguiente firma */ }
                }
            }
            return null;
        }

        public static object? Get(object obj, string name)
        {
            var t = obj.GetType();
            const BindingFlags F = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;

            try
            {
                var p = t.GetProperty(name, F);
                if (p != null)
                {
                    try { return p.GetValue(obj); }
                    catch { }
                }
            }
            catch { }

            try
            {
                var f = t.GetField(name, F);
                if (f != null)
                {
                    try { return f.GetValue(obj); }
                    catch { }
                }
            }
            catch { }

            return null;
        }
    }

    static class Bridge
    {
        const int GEN4_MAX_DEX = 493;
        const int GEN4_MAX_MOVE = 467;

        // ===== Flags / parámetros =====
        struct BridgeArgs
        {
            public string SavPath;
            public string CorePath;
            public int? Box;           // null = todas
            public string Mode;        // "auto" | "prop" | "m0" | "m1" | "m2"
            // Escritura
            public string Op;          // "revive" | "steal" | null
            public string SrcPath;     // origen (revive/steal)
            public string DstPath;     // destino (steal)
            public string Kind;        // "party" | "box"
            public int? Slot;          // índice de slot en origen
        }

        static BridgeArgs ParseArgs(string[] args)
        {
            // Lectura: exe <sav> [core] [--box N] [--mode prop|m0|m1|m2]
            // Escritura:
            //  - Revivir: exe --op revive --src <sav> --box 17 --slot S [core]
            //  - Robar:   exe --op steal --src <victim.sav> --dst <thief.sav> --kind party|box --box B --slot S [core]
            var ba = new BridgeArgs { SavPath = "", CorePath = "", Box = null, Mode = "auto", Op = "", SrcPath = "", DstPath = "", Kind = "box", Slot = null };
            int i = 0;
            // detectar si primer arg es ruta (modo lectura)
            if (i < args.Length && !args[i].StartsWith("--")) { ba.SavPath = args[i++]; }
            if (i < args.Length && !args[i].StartsWith("--")) { ba.CorePath = args[i++]; }

            for (; i < args.Length; i++)
            {
                var a = args[i];
                if (a == "--box" && i+1 < args.Length && int.TryParse(args[i+1], out var b)) { ba.Box = b; i++; }
                else if (a == "--mode" && i+1 < args.Length) { ba.Mode = args[i+1].ToLowerInvariant(); i++; }
                else if (a == "--op" && i+1 < args.Length) { ba.Op = args[i+1].ToLowerInvariant(); i++; }
                else if (a == "--src" && i+1 < args.Length) { ba.SrcPath = args[i+1]; i++; }
                else if (a == "--dst" && i+1 < args.Length) { ba.DstPath = args[i+1]; i++; }
                else if (a == "--kind" && i+1 < args.Length) { ba.Kind = args[i+1].ToLowerInvariant(); i++; }
                else if (a == "--slot" && i+1 < args.Length && int.TryParse(args[i+1], out var s)) { ba.Slot = s; i++; }
            }
            return ba;
        }

        static object? FirstNotNull(params object?[] xs) => xs.FirstOrDefault(x => x != null);

        static string EnumName(Assembly asm, string typeName, int val)
        {
            var et = asm.GetType(typeName);
            if (et == null) return $"#{val}";
            try { return Enum.ToObject(et, val).ToString()!.Replace("_", " "); }
            catch { return $"#{val}"; }
        }

        static string CleanNickname(object? nicknameObj)
        {
            var s = nicknameObj as string ?? "";
            if (string.IsNullOrWhiteSpace(s)) return "";
            var sb = new StringBuilder(s.Length);
            foreach (var ch in s)
            {
                if (ch == '\uffff') continue;
                if (char.IsControl(ch)) continue;
                sb.Append(ch);
            }
            return sb.ToString().Trim();
        }

        static bool LooksValidGen4(object pkm)
        {
            try
            {
                // Para detectar slot ocupado es suficiente con Species v?lido.
                int sp = Convert.ToInt32(Ref.Get(pkm, "Species") ?? 0);
                return sp >= 1 && sp <= GEN4_MAX_DEX;
            }
            catch { return false; }
        }

        // Intenta desempaquetar un posible wrapper de slot (Pokemon/PKM/etc.) hasta llegar al objeto con Species
        static object? AsPKM(object? maybe)
        {
            if (maybe == null) return null;
            if (LooksValidGen4(maybe)) return maybe;
            var names = new[] { "Pokemon", "PKM", "CurrentPKM", "Current", "Data", "Value", "Entity", "Mon" };
            foreach (var n in names)
            {
                try
                {
                    var inner = Ref.Get(maybe, n);
                    if (inner != null && LooksValidGen4(inner)) return inner;
                }
                catch { }
            }
            return null;
        }

        static Dictionary<string, object?> PkmToDto(Assembly core, object pkm, int boxIndex, int slotIndex, string sourceTag)
        {
            int Species = Convert.ToInt32(Ref.Get(pkm, "Species") ?? 0);
            int Level = Convert.ToInt32(Ref.Get(pkm, "CurrentLevel") ?? Ref.Get(pkm, "Level") ?? 0);
            if (Species < 1 || Species > GEN4_MAX_DEX) return new();

            int Nature = Convert.ToInt32(Ref.Get(pkm, "Nature") ?? 0);
            int Ability = Convert.ToInt32(Ref.Get(pkm, "Ability") ?? 0);
            int Form = Convert.ToInt32(Ref.Get(pkm, "Form") ?? 0);
            int Gender = Convert.ToInt32(Ref.Get(pkm, "Gender") ?? 0);

            int Friendship = Convert.ToInt32(FirstNotNull(
                Ref.Get(pkm, "OT_Friendship"), Ref.Get(pkm, "Friendship"), Ref.Get(pkm, "CurrentFriendship")
            ) ?? 0);

            // OT / Owner
            int OT_TID = Convert.ToInt32(FirstNotNull(Ref.Get(pkm, "TID"), Ref.Get(pkm, "TrainerID")) ?? 0);
            int OT_SID = Convert.ToInt32(FirstNotNull(Ref.Get(pkm, "SID"), Ref.Get(pkm, "SecretID")) ?? 0);
            string OT_Name = (Ref.Get(pkm, "OT_Name") as string) ?? (Ref.Get(pkm, "OT") as string) ?? "";

            int IV_HP  = Convert.ToInt32(Ref.Get(pkm, "IV_HP")  ?? 0);
            int IV_ATK = Convert.ToInt32(Ref.Get(pkm, "IV_ATK") ?? 0);
            int IV_DEF = Convert.ToInt32(Ref.Get(pkm, "IV_DEF") ?? 0);
            int IV_SPA = Convert.ToInt32(Ref.Get(pkm, "IV_SPA") ?? 0);
            int IV_SPD = Convert.ToInt32(Ref.Get(pkm, "IV_SPD") ?? 0);
            int IV_SPE = Convert.ToInt32(Ref.Get(pkm, "IV_SPE") ?? 0);

            int EV_HP  = Convert.ToInt32(Ref.Get(pkm, "EV_HP")  ?? 0);
            int EV_ATK = Convert.ToInt32(Ref.Get(pkm, "EV_ATK") ?? 0);
            int EV_DEF = Convert.ToInt32(Ref.Get(pkm, "EV_DEF") ?? 0);
            int EV_SPA = Convert.ToInt32(Ref.Get(pkm, "EV_SPA") ?? 0);
            int EV_SPD = Convert.ToInt32(Ref.Get(pkm, "EV_SPD") ?? 0);
            int EV_SPE = Convert.ToInt32(Ref.Get(pkm, "EV_SPE") ?? 0);

            // Held Item
            int ItemId = Convert.ToInt32(FirstNotNull(Ref.Get(pkm, "HeldItem"), Ref.Get(pkm, "Item")) ?? 0);
            string ItemName = EnumName(core, "PKHeX.Core.Item", ItemId);

            var moves = new List<Dictionary<string, object?>>();
            for (int i = 0; i < 4; i++)
            {
                int moveId = 0;
                var gm = Ref.Call(pkm, "GetMove", i);
                if (gm is not null) moveId = Convert.ToInt32(gm);
                else moveId = Convert.ToInt32(Ref.Get(pkm, $"Move{i + 1}") ?? 0);
                if (moveId <= 0 || moveId > GEN4_MAX_MOVE) continue;

                int pp = 0;
                var mpp1 = Ref.Call(pkm, "GetMovePP", i);
                if (mpp1 is not null) pp = Convert.ToInt32(mpp1);
                else
                {
                    try { pp = Convert.ToInt32(Ref.Call(pkm, "GetMovePP", (ushort)moveId, 0) ?? 0); }
                    catch { }
                }

                moves.Add(new() { ["Name"] = EnumName(core, "PKHeX.Core.Move", moveId), ["MoveId"] = moveId, ["PP"] = pp });
            }

            return new()
            {
                ["Species"] = EnumName(core, "PKHeX.Core.Species", Species),
                ["SpeciesId"] = Species,
                ["Level"] = Level,
                ["Nature"] = EnumName(core, "PKHeX.Core.Nature", Nature),
                ["Ability"] = EnumName(core, "PKHeX.Core.Ability", Ability),
                ["AbilityId"] = Ability,
                ["Form"] = Form,
                ["Gender"] = Gender,
                ["Friendship"] = Friendship,
                ["ItemId"] = ItemId,
                ["Item"] = ItemName,
                ["HP_IV"] = IV_HP, ["ATK_IV"] = IV_ATK, ["DEF_IV"] = IV_DEF,
                ["SPA_IV"] = IV_SPA, ["SPD_IV"] = IV_SPD, ["SPE_IV"] = IV_SPE,
                ["HP_EV"] = EV_HP, ["ATK_EV"] = EV_ATK, ["DEF_EV"] = EV_DEF,
                ["SPA_EV"] = EV_SPA, ["SPD_EV"] = EV_SPD, ["SPE_EV"] = EV_SPE,
                ["Nickname"] = CleanNickname(Ref.Get(pkm, "Nickname")),
                ["Moves"] = moves,
                ["BoxIndex"] = boxIndex,
                ["SlotIndex"] = slotIndex,
                ["Source"] = sourceTag,
                ["OT_TID"] = OT_TID,
                ["OT_SID"] = OT_SID,
                ["OT_Name"] = OT_Name,
            };
        }

        static bool IsPkm(object? o) => o != null && LooksValidGen4(o);
        static int CountEnumerable(IEnumerable e) { int n=0; foreach(var _ in e) n++; return n; }

        static List<Dictionary<string, object?>> DumpBox(Assembly core, object sav, IEnumerable slots, int bIndex, string? name, string sourceTag)
        {
            var mons = new List<Dictionary<string, object?>>();
            int sIdx = 0;
            foreach (var pkm in slots)
            {
                var ent = AsPKM(pkm);
                if (ent != null)
                {
                    var dto = PkmToDto(core, ent, bIndex, sIdx, sourceTag);
                    if (dto.Count > 0) mons.Add(dto);
                }
                sIdx++;
            }
            string finalName = name
                ?? (Ref.Call(sav, "GetBoxName", bIndex) as string)
                ?? (Ref.Get(sav, "BoxNames") as Array)?.GetValue(bIndex)?.ToString()
                ?? $"Caja {bIndex + 1}";
            return new() { new() { ["Name"] = finalName, ["Index"] = bIndex, ["Mons"] = mons } };
        }

        static IEnumerable? GetBoxesCollectionRaw(object sav)
        {
            object? boxes =
                Ref.Get(sav, "Boxes")
                ?? Ref.Get(Ref.Get(sav, "PC") ?? new object(), "Boxes")
                ?? Ref.Get(Ref.Get(sav, "Storage") ?? new object(), "Boxes")
                ?? Ref.Get(sav, "AllBoxes");
            return boxes as IEnumerable;
        }

        // === Estrategia "prop": usar la colecci?n Boxes y sus listas internas ===
        static List<Dictionary<string, object?>> GetBoxesProp(Assembly core, object sav, int? onlyBox = null)
        {
            var outList = new List<Dictionary<string, object?>>();
            var boxesEnum = GetBoxesCollectionRaw(sav);
            if (boxesEnum == null) return outList;

            var boxes = new List<object?>();
            foreach (var b in boxesEnum) boxes.Add(b);

            int start = onlyBox.HasValue ? onlyBox.Value : 0;
            int end   = onlyBox.HasValue ? onlyBox.Value : boxes.Count - 1;
            start = Math.Max(0, start); end = Math.Min(end, boxes.Count - 1);

            for (int idx = start; idx <= end; idx++)
            {
                var b = boxes[idx];
                if (b == null) continue;

                IEnumerable? slots =
                    Ref.Get(b, "Mons")    as IEnumerable ??
                    Ref.Get(b, "Pokemon") as IEnumerable ??
                    Ref.Get(b, "Slots")   as IEnumerable ??
                    Ref.Get(b, "BoxMons") as IEnumerable;

                if (slots == null) continue;

                string? name = Ref.Get(b, "Name") as string
                               ?? Ref.Call(sav, "GetBoxName", idx) as string
                               ?? (Ref.Get(sav, "BoxNames") as Array)?.GetValue(idx)?.ToString()
                               ?? $"Caja {idx + 1}";

                outList.AddRange(DumpBox(core, sav, slots, idx, name, "prop"));
                if (onlyBox.HasValue) break;
            }
            return outList;
        }

        // === Estrategia "method": forzar una firma concreta ===
        static List<Dictionary<string, object?>> GetBoxesByMethodForced(Assembly core, object sav, int mode, int? onlyBox = null)
        {
            var result = new List<Dictionary<string, object?>>();
            int boxCount = Convert.ToInt32(Ref.Get(sav, "BoxCount") ?? 18);
            int boxSlots = Convert.ToInt32(Ref.Get(sav, "BoxSlotCount") ?? 30);

            // Resolver din?micamente la firma correcta para obtener slots
            Func<int,int,object?> get = (b,s) => null;
            var t = sav.GetType();

            bool IsAllIntParams(ParameterInfo[] ps) => ps.All(p =>
                p.ParameterType == typeof(int) || p.ParameterType == typeof(short) ||
                p.ParameterType == typeof(ushort) || p.ParameterType == typeof(byte) ||
                p.ParameterType == typeof(sbyte));

            MethodInfo? Find(string name, int paramCount)
                => t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                    .FirstOrDefault(m => m.Name == name && m.GetParameters().Length == paramCount && IsAllIntParams(m.GetParameters()));

            MethodInfo? FindAny(string[] names, int paramCount)
            {
                foreach (var nm in names)
                {
                    var mi = Find(nm, paramCount);
                    if (mi != null) return mi;
                }
                return null;
            }

            var names2 = new[] { "GetBoxSlot", "GetPCSlot", "GetDecryptedBoxSlot", "GetBoxPKM", "GetSlot", "GetBoxSlotAtIndex" };
            var names1 = new[] { "GetBoxSlot", "GetPCSlot", "GetDecryptedBoxSlot", "GetBoxPKM", "GetSlot", "GetBoxSlotAtIndex" };

            var m2 = FindAny(names2, 2);
            var m1 = FindAny(names1, 1);
            string getterName = m2?.Name ?? m1?.Name ?? "";

            if (m2 != null)
            {
                get = (b,s) => Ref.Call(sav, getterName, b, s);
            }
            else if (m1 != null)
            {
                get = (b,s) => Ref.Call(sav, getterName, b * boxSlots + s);
            }
            else
            {
                // Fallback robusto: usar propiedades (equivale a "prop")
                return GetBoxesProp(core, sav, onlyBox);
            }

            int startB = onlyBox.HasValue ? Math.Clamp(onlyBox.Value, 0, boxCount-1) : 0;
            int endB   = onlyBox.HasValue ? startB : boxCount-1;

            for (int b = startB; b <= endB; b++)
            {
                var mons = new List<Dictionary<string, object?>>();
                for (int s = 0; s < boxSlots; s++)
                {
                    var el = get(b, s);
                    var pkm = AsPKM(el);
                    if (pkm == null) continue;
                    var dto = PkmToDto(core, pkm!, b, s, "method");
                    if (dto.Count > 0) mons.Add(dto);
                }
                string name = Ref.Call(sav, "GetBoxName", b) as string
                              ?? (Ref.Get(sav, "BoxNames") as Array)?.GetValue(b)?.ToString()
                              ?? $"Caja {b + 1}";
                result.Add(new() { ["Name"] = name, ["Index"] = b, ["Mons"] = mons });
                if (onlyBox.HasValue) break;
            }
            return result;
        }

        // === Auto: prueba prop; si no, prueba m0/m1/m2 ===
        static List<Dictionary<string, object?>> GetBoxesSmart(Assembly core, object sav, string mode, int? onlyBox)
        {
            if (mode == "prop")
                return GetBoxesProp(core, sav, onlyBox);

            if (mode == "m0" || mode == "m1" || mode == "m2")
                return GetBoxesByMethodForced(core, sav, mode == "m0" ? 0 : mode == "m1" ? 1 : 2, onlyBox);

            // auto
            var prop = GetBoxesProp(core, sav, onlyBox);
            // Solo aceptar 'prop' si contiene al menos un mon real
            bool anyPropMons = prop.Any(b => {
                if (!b.TryGetValue("Mons", out var mv)) return false;
                var en = mv as IEnumerable; return en != null && en.Cast<object>().Any();
            });
            if (anyPropMons)
                return prop;

            for (int m = 0; m < 3; m++)
            {
                var via = GetBoxesByMethodForced(core, sav, m, onlyBox);
                bool anyViaMons = via.Any(b => {
                    if (!b.TryGetValue("Mons", out var mv)) return false;
                    var en = mv as IEnumerable; return en != null && en.Cast<object>().Any();
                });
                if (anyViaMons)
                    return via;
            }
            return new();
        }

        // ==== Helpers de escritura ====
        static bool IsAllInt(ParameterInfo[] ps) => ps.All(p => {
            var pt = p.ParameterType; if (pt.IsByRef) pt = pt.GetElementType()!;
            return pt == typeof(int) || pt == typeof(short) || pt == typeof(ushort) || pt == typeof(byte) || pt == typeof(long) || pt == typeof(uint);
        });

        delegate object? GetBoxDel(int b, int s);
        delegate object? GetBoxByIndexDel(int idx);
        delegate void SetBoxDel(int b, int s, object? pkm);
        delegate void SetBoxByIndexDel(int idx, object? pkm);
        delegate object? GetPartyDel(int s);
        delegate void SetPartyDel(int s, object? pkm);

        static bool LooksEmpty(object? pkm) => pkm == null || ! (pkm != null && LooksValidGen4(pkm));

        static void DetectAccessors(object sav, out GetBoxDel? getBox, out GetBoxByIndexDel? getBoxIdx, out SetBoxDel? setBox, out SetBoxByIndexDel? setBoxIdx, out GetPartyDel? getParty, out SetPartyDel? setParty)
        {
            getBox = null; getBoxIdx = null; setBox = null; setBoxIdx = null; getParty = null; setParty = null;
            var t = sav.GetType();
            bool IsNames(MethodInfo m, string key) => m.Name.ToLowerInvariant().Contains(key);
            foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
            {
                var ps = m.GetParameters();
                try
                {
                    if (IsNames(m, "get") && IsNames(m, "box") && ps.Length == 2 && IsAllInt(ps)) getBox = (b, s) => Ref.Call(sav, m.Name, b, s);
                    else if (IsNames(m, "get") && IsNames(m, "box") && ps.Length == 1 && IsAllInt(ps)) getBoxIdx = (i) => Ref.Call(sav, m.Name, i);
                    else if (IsNames(m, "set") && IsNames(m, "box") && ps.Length == 3 && IsAllInt(new[] { ps[0], ps[1] })) setBox = (b, s, p) => Ref.Call(sav, m.Name, b, s, p);
                    else if (IsNames(m, "set") && IsNames(m, "box") && ps.Length == 2 && IsAllInt(new[] { ps[0] })) setBoxIdx = (i, p) => Ref.Call(sav, m.Name, i, p);
                    else if (IsNames(m, "get") && IsNames(m, "party") && ps.Length == 1 && IsAllInt(ps)) getParty = (s) => Ref.Call(sav, m.Name, s);
                    else if (IsNames(m, "set") && IsNames(m, "party") && ps.Length == 2 && IsAllInt(new[] { ps[0] })) setParty = (s, p) => Ref.Call(sav, m.Name, s, p);
                }
                catch { }
            }
        }

        static (int box, int slot) FindFirstFreeSlot(object sav, GetBoxDel? getBox, GetBoxByIndexDel? getBoxIdx)
        {
            for (int b = 0; b < 18; b++)
            {
                if (b == 17) continue; // ignorar caja de muertos
                for (int s = 0; s < 30; s++)
                {
                    object? el = getBox != null ? getBox(b, s) : (getBoxIdx != null ? getBoxIdx(b * 30 + s) : null);
                    if (LooksEmpty(el)) return (b, s);
                }
            }
            return (-1, -1);
        }

        static void ClearSlot(object sav, int box, int slot, SetBoxDel? setBox, SetBoxByIndexDel? setBoxIdx, GetBoxDel? getBox, GetBoxByIndexDel? getBoxIdx)
        {
            if (setBox != null) { try { setBox(box, slot, null); return; } catch { } }
            if (setBoxIdx != null) { try { setBoxIdx(box * 30 + slot, null); return; } catch { } }
            // fallback: reescribir el mismo con especies=0
            object? p = getBox != null ? getBox(box, slot) : (getBoxIdx != null ? getBoxIdx(box * 30 + slot) : null);
            if (p != null)
            {
                try { Ref.Call(p, "Clear"); } catch { try { Ref.Call(p, "SetSpecies", 0); } catch { } }
                if (setBox != null) setBox(box, slot, p);
                else if (setBoxIdx != null) setBoxIdx(box * 30 + slot, p);
            }
        }

        static bool SaveToPath(Assembly coreAsm, object sav, string path)
        {
            try
            {
                var dir = Path.GetDirectoryName(path);
                if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
                if (File.Exists(path))
                {
                    var at = File.GetAttributes(path);
                    if (at.HasFlag(FileAttributes.ReadOnly)) File.SetAttributes(path, at & ~FileAttributes.ReadOnly);
                }
            }
            catch { }
            var tSav = sav.GetType();
            string[] candidates = new[] { "Write", "Save", "Export" };
            // 1) Métodos de instancia que devuelven byte[] sin parámetros
            foreach (var m in tSav.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
            {
                var name = m.Name.ToLowerInvariant();
                if ((name.Contains("write") || name.Contains("export") || name.Contains("save")) && m.GetParameters().Length == 0 && m.ReturnType == typeof(byte[]))
                {
                    try { var data = (byte[])m.Invoke(sav, null)!; File.WriteAllBytes(path, data); return true; } catch { }
                }
            }
            // 2) Métodos de instancia con (string path) y retorno void/bool
            foreach (var m in tSav.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
            {
                var ps = m.GetParameters();
                var name = m.Name.ToLowerInvariant();
                if ((name.Contains("write") || name.Contains("export") || name.Contains("save")) && ps.Length == 1 && ps[0].ParameterType == typeof(string))
                {
                    try { var r = m.Invoke(sav, new object?[] { path }); if (r is bool b) return b; else return true; } catch { }
                }
            }
            // 3) SaveUtil estático (sav, path) en variantes
            var tSaveUtil = coreAsm.GetType("PKHeX.Core.SaveUtil");
            if (tSaveUtil != null)
            {
                foreach (var m in tSaveUtil.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static))
                {
                    var ps = m.GetParameters();
                    var name = m.Name.ToLowerInvariant();
                    if ((name.Contains("write") || name.Contains("export") || name.Contains("save")) && ps.Length == 2 &&
                        ((ps[1].ParameterType == typeof(string) && ps[0].ParameterType.IsAssignableFrom(tSav)) ||
                         (ps[0].ParameterType == typeof(string) && ps[1].ParameterType.IsAssignableFrom(tSav))))
                    {
                        try
                        {
                            if (ps[1].ParameterType == typeof(string))
                            {
                                var r = m.Invoke(null, new object?[] { sav, path }); if (r is bool b) return b; else return true;
                            }
                            else
                            {
                                var r = m.Invoke(null, new object?[] { path, sav }); if (r is bool b) return b; else return true;
                            }
                        }
                        catch { }
                    }
                    // Fallback: byte[] method with (sav)
                    if ((name.Contains("write") || name.Contains("export") || name.Contains("save") || name.Contains("bytes"))
                        && ps.Length == 1 && ps[0].ParameterType.IsAssignableFrom(tSav) && m.ReturnType == typeof(byte[]))
                    {
                        try { var data = (byte[])m.Invoke(null, new object?[] { sav })!; File.WriteAllBytes(path, data); return true; } catch { }
                    }
                }
            }
            // 4) Instance(Stream) or (BinaryWriter)
            foreach (var m in tSav.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
            {
                var ps = m.GetParameters();
                var name = m.Name.ToLowerInvariant();
                if (!(name.Contains("write") || name.Contains("export") || name.Contains("save"))) continue;
                if (ps.Length != 1) continue;
                var pt = ps[0].ParameterType;
                if (pt == typeof(Stream) || pt == typeof(BinaryWriter))
                {
                    try
                    {
                        var tmp = path + ".tmp";
                        using var fs = new FileStream(tmp, FileMode.Create, FileAccess.Write, FileShare.None);
                        object? arg = pt == typeof(BinaryWriter) ? new BinaryWriter(fs, Encoding.UTF8, true) : (object)fs;
                        m.Invoke(sav, new object?[] { arg });
                        fs.Flush(true);
                        (arg as BinaryWriter)?.Flush();
                        File.Copy(tmp, path, true);
                        File.Delete(tmp);
                        return true;
                    }
                    catch { }
                }
            }
            // 5) Instance Write(BinaryExportSetting) -> byte[]
            try
            {
                var tSetting = coreAsm.GetType("PKHeX.Core.BinaryExportSetting");
                if (tSetting != null)
                {
                    object? setting = null;
                    try { setting = tSetting.GetProperty("Default", BindingFlags.Public | BindingFlags.Static)?.GetValue(null); } catch { }
                    if (setting == null) { try { setting = Activator.CreateInstance(tSetting); } catch { setting = null; } }
                    if (setting != null)
                    {
                        foreach (var m in tSav.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
                        {
                            if (!string.Equals(m.Name, "Write", StringComparison.OrdinalIgnoreCase)) continue;
                            var ps = m.GetParameters();
                            if (ps.Length != 1) continue;
                            if (ps[0].ParameterType.IsAssignableFrom(tSetting))
                            {
                                try
                                {
                                    var res = m.Invoke(sav, new object?[] { setting });
                                    if (res is byte[] data) { File.WriteAllBytes(path, data); return true; }
                                }
                                catch { }
                            }
                        }
                    }
                }
            }
            catch { }

            try
            {
                Console.Error.WriteLine("SaveToPath: no matching save method");
                Console.Error.WriteLine("Save class: " + tSav.FullName);
                var meths = tSav.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)
                    .Where(mm => {
                        var n = mm.Name.ToLowerInvariant();
                        return n.Contains("write") || n.Contains("export") || n.Contains("save");
                    })
                    .Select(mm => mm.Name + "(" + string.Join(",", mm.GetParameters().Select(p => p.ParameterType.Name)) + ")" );
                Console.Error.WriteLine("Save methods: " + string.Join("; ", meths));
            }
            catch { }
            
            
            return false;
        }

        static Dictionary<string, object?> BuildOutput(Assembly coreAsm, object sav, object info, string mode, int? onlyBox)
        {
            var trainer = new Dictionary<string, object?>()
            {
                ["Name"] = Ref.Get(sav, "OT") as string ?? "",
                ["TID"]  = Convert.ToInt32(Ref.Get(sav, "TID") ?? 0),
                ["SID"]  = Convert.ToInt32(Ref.Get(sav, "SID") ?? 0),
                ["Money"] = Convert.ToInt32(Ref.Get(sav, "Money") ?? 0),
                ["Badges"] = Convert.ToInt32(Ref.Get(sav, "Badges") ?? 0),
                ["PlayTimeHours"] = Convert.ToInt32(Ref.Get(sav, "PlayedHours") ?? 0),
                ["PlayTimeMinutes"] = Convert.ToInt32(Ref.Get(sav, "PlayedMinutes") ?? 0),
            };

            var partyOut = new List<Dictionary<string, object?>>();
            var party = Ref.Get(sav, "PartyData") as IEnumerable ?? Ref.Get(sav, "Party") as IEnumerable;
            if (party != null)
            {
                int sIdx = 0;
                foreach (var el in party)
                {
                    var pkm = AsPKM(el);
                    if (pkm != null)
                    {
                        var dto = PkmToDto(coreAsm, pkm, -1, sIdx, "party");
                        if (dto.Count > 0) partyOut.Add(dto);
                    }
                    sIdx++;
                }
            }

            var boxesOut = GetBoxesSmart(coreAsm, sav, mode, onlyBox);
            int boxCount = 0;
            try
            {
                boxCount = Convert.ToInt32(Ref.Get(sav, "BoxCount") ?? (boxesOut?.Count ?? 0));
            }
            catch { boxCount = boxesOut?.Count ?? 0; }

            return new()
            {
                ["Game"] = Ref.Get(info, "Description") as string ?? "Unknown",
                ["SaveClass"] = sav.GetType().Name,
                ["BoxCount"] = boxCount,
                ["Trainer"] = trainer,
                ["Party"] = new Dictionary<string, object?> { ["Mons"] = partyOut },
                ["Boxes"] = boxesOut,
                ["BridgeTag"] = "pc-probed-v7j"
            };
        }

        static bool TryOpenSave(Assembly coreAsm, string savPath, out object? sav, out object? info)
        {
            sav = null; info = null;
            var tSaveUtil = coreAsm.GetType("PKHeX.Core.SaveUtil");
            if (tSaveUtil == null) { Console.Error.WriteLine(""); return false; }

            var names = new[] { "GetVariantSAV", "GetSAV", "Open", "Load", "Read", "FromPath", "TryGetSAV", "TryOpen" };
            foreach (var m in tSaveUtil.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static))
            {
                if (!names.Contains(m.Name)) continue;
                var ps = m.GetParameters();
                try
                {
                    if (m.Name.StartsWith("Try"))
                    {
                        var argsTry = new object?[ps.Length];
                        for (int i = 0; i < ps.Length; i++)
                        {
                            var pt = ps[i].ParameterType;
                            if (pt == typeof(string)) argsTry[i] = savPath;
                            else if (pt.IsByRef) argsTry[i] = null;
                            else argsTry[i] = null;
                        }
                        var ok = (bool)(m.Invoke(null, argsTry) ?? false);
                        if (!ok) { Console.Error.WriteLine($""); continue; }

                        foreach (var (p, idx) in ps.Select((p, i) => (p, i)))
                        {
                            if (p.IsOut || p.ParameterType.IsByRef)
                            {
                                var val = argsTry[idx];
                                if (sav == null && val != null && val.GetType().Name.StartsWith("SAV"))
                                    sav = val;
                                else if (info == null && val != null)
                                    info = val;
                            }
                        }
                    }
                    else
                    {
                        object?[]? args = ps.Length switch
                        {
                            1 => new object?[] { savPath },
                            2 when ps[1].IsOut || ps[1].ParameterType.IsByRef => new object?[] { savPath, null },
                            _ => null
                        };
                        if (args == null) continue;

                        var r = m.Invoke(null, args);
                        if (r != null) { sav = r; if (ps.Length == 2) info = args[1]; }
                    }
                }
                catch (Exception) { continue; }

                if (sav != null) return true;
            }
            return false;
        }

        public static int Run(string[] args)
        {
            var par = ParseArgs(args);
            // Operaciones de escritura
            if (!string.IsNullOrWhiteSpace(par.Op))
            {
                try
                {
                    string? ResolveCorePath(string? arg)
                    {
                        string? take(string? p)
                        {
                            if (string.IsNullOrWhiteSpace(p)) return null;
                            if (File.Exists(p)) return p;
                            if (Directory.Exists(p))
                            {
                                var cand = Path.Combine(p, "PKHeX.Core.dll");
                                if (File.Exists(cand)) return cand;
                            }
                            return null;
                        }
                        var core = take(arg);
                        if (core != null) return core;
                        core = take(Environment.GetEnvironmentVariable("PKHEX_CORE_PATH"));
                        if (core != null) return core;
                        var exeDir = AppContext.BaseDirectory;
                        string? dir = exeDir;
                        for (int i = 0; i < 6 && !string.IsNullOrEmpty(dir); i++)
                        {
                            var cand = Path.Combine(dir!, "PKHeX.Core.dll");
                            if (File.Exists(cand)) return cand;
                            dir = Directory.GetParent(dir!)?.FullName;
                        }
                        var cwdCand = Path.Combine(Environment.CurrentDirectory, "PKHeX.Core.dll");
                        if (File.Exists(cwdCand)) return cwdCand;
                        return null;
                    }
                    var corePath = ResolveCorePath(par.CorePath);
                    if (string.IsNullOrWhiteSpace(corePath) || !File.Exists(corePath))
                    { Console.Error.WriteLine("No encuentro PKHeX.Core.dll."); return 5; }
                    var coreAsm = Assembly.LoadFrom(corePath);

                    if (par.Op == "revive")
                    {
                        if (string.IsNullOrWhiteSpace(par.SrcPath) || par.Slot == null)
                        { Console.Error.WriteLine("Faltan parámetros para revive: --src y --slot"); return 2; }
                        if (!TryOpenSave(coreAsm, par.SrcPath, out var sav, out var info) || sav == null)
                        { Console.Error.WriteLine("No se pudo abrir el save src."); return 6; }
                        DetectAccessors(sav, out var gB, out var gBIdx, out var sB, out var sBIdx, out var gP, out var sP);
                        if (gB == null && gBIdx == null) { Console.Error.WriteLine("No se pudo resolver acceso a cajas."); return 10; }
                        int srcBox = par.Box ?? 17; int srcSlot = par.Slot.Value;
                        object? mon = gB != null ? gB(srcBox, srcSlot) : gBIdx!(srcBox * 30 + srcSlot);
                        if (LooksEmpty(mon)) { Console.Error.WriteLine("Slot vacío."); return 11; }
                        var dest = FindFirstFreeSlot(sav, gB, gBIdx);
                        if (dest.box < 0) { Console.Error.WriteLine("No hay hueco disponible."); return 12; }
                        if (sB != null) sB(dest.box, dest.slot, mon);
                        else if (sBIdx != null) sBIdx(dest.box * 30 + dest.slot, mon);
                        ClearSlot(sav, srcBox, srcSlot, sB, sBIdx, gB, gBIdx);
                        // Backup y aseguramos permisos de escritura
                        File.Copy(par.SrcPath, par.SrcPath + ".bak", true);
                        try { var at = File.GetAttributes(par.SrcPath); if ((at & FileAttributes.ReadOnly) != 0) File.SetAttributes(par.SrcPath, at & ~FileAttributes.ReadOnly); } catch {}
                        if (!SaveToPath(coreAsm, sav, par.SrcPath)) { Console.Error.WriteLine("No se pudo guardar el save src. Cierra el emulador/juego si está usando el archivo."); return 13; }
                        Console.WriteLine("{\"status\":\"ok\",\"op\":\"revive\"}");
                        return 0;
                    }
                    else if (par.Op == "steal")
                    {
                        if (string.IsNullOrWhiteSpace(par.SrcPath) || string.IsNullOrWhiteSpace(par.DstPath) || par.Slot == null)
                        { Console.Error.WriteLine("Faltan parámetros para steal: --src --dst --kind --slot [--box]"); return 2; }
                        if (!TryOpenSave(coreAsm, par.SrcPath, out var srcSav, out var srcInfo) || srcSav == null)
                        { Console.Error.WriteLine("No se pudo abrir el save src."); return 6; }
                        if (!TryOpenSave(coreAsm, par.DstPath, out var dstSav, out var dstInfo) || dstSav == null)
                        { Console.Error.WriteLine("No se pudo abrir el save dst."); return 6; }
                        DetectAccessors(srcSav, out var gB1, out var gBIdx1, out var sB1, out var sBIdx1, out var gP1, out var sP1);
                        DetectAccessors(dstSav, out var gB2, out var gBIdx2, out var sB2, out var sBIdx2, out var gP2, out var sP2);
                        if ((gB2 == null && gBIdx2 == null) || (sB2 == null && sBIdx2 == null)) { Console.Error.WriteLine("No se pudo resolver acceso a cajas destino."); return 10; }
                        object? mon = null;
                        if ((par.Kind ?? "box") == "party")
                        {
                            if (gP1 == null) { Console.Error.WriteLine("No se pudo acceder al equipo del origen."); return 10; }
                            mon = gP1(par.Slot.Value);
                            if (LooksEmpty(mon)) { Console.Error.WriteLine("Slot vacío."); return 11; }
                            if (sP1 != null) sP1(par.Slot.Value, null);
                        }
                        else
                        {
                            int b = par.Box ?? 0; int s = par.Slot.Value;
                            mon = gB1 != null ? gB1(b, s) : gBIdx1!(b * 30 + s);
                            if (LooksEmpty(mon)) { Console.Error.WriteLine("Slot vacío."); return 11; }
                            ClearSlot(srcSav, b, s, sB1, sBIdx1, gB1, gBIdx1);
                        }
                        var dest = FindFirstFreeSlot(dstSav, gB2, gBIdx2);
                        if (dest.box < 0) { Console.Error.WriteLine("No hay hueco disponible en destino."); return 12; }
                        if (sB2 != null) sB2(dest.box, dest.slot, mon);
                        else if (sBIdx2 != null) sBIdx2(dest.box * 30 + dest.slot, mon);
                        File.Copy(par.SrcPath, par.SrcPath + ".bak", true);
                        File.Copy(par.DstPath, par.DstPath + ".bak", true);
                        try { var at = File.GetAttributes(par.SrcPath); if ((at & FileAttributes.ReadOnly) != 0) File.SetAttributes(par.SrcPath, at & ~FileAttributes.ReadOnly); } catch {}
                        try { var at = File.GetAttributes(par.DstPath); if ((at & FileAttributes.ReadOnly) != 0) File.SetAttributes(par.DstPath, at & ~FileAttributes.ReadOnly); } catch {}
                        if (!SaveToPath(coreAsm, srcSav, par.SrcPath)) { Console.Error.WriteLine("No se pudo guardar el save src. Cierra el emulador/juego si está usando el archivo."); return 13; }
                        if (!SaveToPath(coreAsm, dstSav, par.DstPath)) { Console.Error.WriteLine("No se pudo guardar el save dst. Cierra el emulador/juego si está usando el archivo."); return 13; }
                        Console.WriteLine("{\"status\":\"ok\",\"op\":\"steal\"}");
                        return 0;
                    }
                    Console.Error.WriteLine("Operación no soportada.");
                    return 2;
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine("ERROR: " + ex.ToString());
                    return 1;
                }
            }

            if (string.IsNullOrWhiteSpace(par.SavPath))
            {
                Console.Error.WriteLine("Uso: PKHeXBridge <ruta_al_save.sav> [ruta_PKHeX.Core.dll] [--box N] [--mode prop|m0|m1|m2]");
                return 2;
            }

            var savPath = par.SavPath;
            if (!File.Exists(savPath))
            {
                Console.Error.WriteLine($"No existe el archivo: {savPath}");
                return 3;
            }

            try
            {
                                // Resolve PKHeX.Core.dll path robustly
                string? ResolveCorePath(string? arg)
                {
                    string? take(string? p)
                    {
                        if (string.IsNullOrWhiteSpace(p)) return null;
                        if (File.Exists(p)) return p;
                        if (Directory.Exists(p))
                        {
                            var cand = Path.Combine(p, "PKHeX.Core.dll");
                            if (File.Exists(cand)) return cand;
                        }
                        return null;
                    }
                    var core = take(arg);
                    if (core != null) return core;
                    core = take(Environment.GetEnvironmentVariable("PKHEX_CORE_PATH"));
                    if (core != null) return core;
                    var exeDir = AppContext.BaseDirectory;
                    string? dir = exeDir;
                    for (int i = 0; i < 6 && !string.IsNullOrEmpty(dir); i++)
                    {
                        var cand = Path.Combine(dir!, "PKHeX.Core.dll");
                        if (File.Exists(cand)) return cand;
                        dir = Directory.GetParent(dir!)?.FullName;
                    }
                    var cwdCand = Path.Combine(Environment.CurrentDirectory, "PKHeX.Core.dll");
                    if (File.Exists(cwdCand)) return cwdCand;
                    return null;
                }

                var corePath = ResolveCorePath(par.CorePath);
                if (string.IsNullOrWhiteSpace(corePath) || !File.Exists(corePath))
                {
                    Console.Error.WriteLine("No encuentro PKHeX.Core.dll. Indica su ruta (archivo o carpeta) como segundo argumento o define PKHEX_CORE_PATH.");
                    return 5;
                }

                var coreAsm = Assembly.LoadFrom(corePath);

                if (!TryOpenSave(coreAsm, savPath, out var sav, out var info) || sav == null)
                {
                    Console.Error.WriteLine("No se pudo abrir el .sav.");
                    return 6;
                }

            var gen = Ref.Get(sav, "Generation");
            if (gen != null)
            {
                var g = Convert.ToInt32(gen);
                if (g != 3 && g != 4)
                {
                    Console.Error.WriteLine($"El guardado no es de Gen 3/4 (detectado Gen {gen}).");
                    return 7;
                }
            }

            var output = BuildOutput(coreAsm, sav, info ?? new { Description = "Unknown" }, par.Mode, par.Box);
            Console.WriteLine(JsonSerializer.Serialize(output));
            return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("ERROR: " + ex.ToString());
                return 1;
            }
        }
    }

    internal static class Program
    {
        public static int Main(string[] args) => Bridge.Run(args);
    }
}














