// Points BP_DIS's ReceiveTick event at the ubergraph offset CompleteCurrentPrompt
// uses, so a prompt is completed the moment the actor starts ticking for it.
//
// Both offsets are READ FROM THE ASSET by function name, never hardcoded. A game
// patch that recompiles BP_DIS renumbers every offset; because this derives them
// on each run, the same command keeps working. That is the whole reason this is
// a tool rather than a recorded byte edit.
//
// Why ReceiveTick and not StartCurrentPrompt: a Blueprint calling its own event
// does not go through the event's thunk - the compiler emits a direct jump into
// the ubergraph - so redirecting a thunk only affects callers OUTSIDE the
// Blueprint. StartCurrentPrompt has none. ReceiveTick is invoked natively by the
// engine through ProcessEvent, always through the thunk. See tools/pak/README.md.
//
//   dotnet run -- <asset.uasset> <mappings.usmap> <out.uasset> [mode] [options]
//
// Modes, first one present wins (fixed precedence, not argument order):
//   --classify <dir>       print every .uasset under <dir> with its export classes
//   --enum <Name>          a usmap enum's values in index order
//   --list-props           every export's properties, data-table rows included
//   --list-imports         what the asset references
//   --list-functions       every function export and its ubergraph entry offset
//   --list-defaults        the class default object's properties, recursively
//   --roundtrip-only       re-serialise unchanged; require byte-identical output
//   --set-enum=Name:Value  edit class defaults (also --set-double=Name:Value);
//                          re-read and verified unconditionally
//   (default)              redirect --from <event> (ReceiveTick) to
//                          --to <event> (CompleteCurrentPrompt); --verify re-reads
//                          the result and bounds the bytes that changed
using System.Globalization;
using UAssetAPI;
using UAssetAPI.ExportTypes;
using UAssetAPI.Kismet.Bytecode;
using UAssetAPI.Kismet.Bytecode.Expressions;
using UAssetAPI.PropertyTypes.Objects;
using UAssetAPI.UnrealTypes;
using UAssetAPI.Unversioned;

static class Patcher
{
    const string DEFAULT_FROM = "ReceiveTick";
    const string DEFAULT_TO = "CompleteCurrentPrompt";
    const EngineVersion VER = EngineVersion.VER_UE5_5;

    // Precedence when several mode flags are given. Keep this order: callers
    // (build_pak.py, list_dis_scenes.py) rely on it and on the "x" placeholders
    // --classify accepts for the asset paths it never opens.
    static readonly string[] MODES =
        { "--classify", "--enum", "--list-props", "--list-imports", "--list-functions", "--list-defaults", "--roundtrip-only", "--set" };

    static int Main(string[] argv)
    {
        if (argv.Length < 3)
        {
            Console.Error.WriteLine("usage: patcher <asset.uasset> <mappings.usmap> <out.uasset> [mode] [options]");
            Console.Error.WriteLine("  modes:   --classify <dir> | --enum <Name> | --list-props | --list-imports");
            Console.Error.WriteLine("           | --list-functions | --list-defaults | --roundtrip-only");
            Console.Error.WriteLine("           | --set-enum=Name:Value / --set-double=Name:Value");
            Console.Error.WriteLine($"  default: redirect --from <event> ({DEFAULT_FROM}) to --to <event> ({DEFAULT_TO}) [--verify]");
            return 2;
        }
        if (argv.Contains("--set-enum") || argv.Contains("--set-double"))
        {
            Console.Error.WriteLine("--set-enum and --set-double take =Name:Value");
            return 2;
        }
        string src = argv[0], usmap = argv[1], dst = argv[2];
        string mode = MODES.FirstOrDefault(m => m == "--set"
                ? argv.Any(a => a.StartsWith("--set-enum=") || a.StartsWith("--set-double="))
                : argv.Contains(m)) ?? "--patch";

        var map = new Usmap(usmap);
        switch (mode)
        {
            case "--classify":       return Classify(ArgAfter(argv, "--classify"), map);
            case "--enum":           return ListEnum(ArgAfter(argv, "--enum"), map);
            case "--list-props":     return ListProps(Load(src, map));
            case "--list-imports":   return ListImports(Load(src, map));
            case "--list-functions": return ListFunctions(Load(src, map));
            case "--list-defaults":  return ListDefaults(Load(src, map));
            case "--roundtrip-only": return RoundTrip(Load(src, map), src, dst);
            case "--set":            return EditDefaults(Load(src, map), dst, map, argv);
            default:
                return PatchThunk(Load(src, map), src, dst, map,
                                  argv.Contains("--from") ? ArgAfter(argv, "--from") : DEFAULT_FROM,
                                  argv.Contains("--to")   ? ArgAfter(argv, "--to")   : DEFAULT_TO,
                                  argv.Contains("--verify"));
        }
    }

    // ---- shared helpers ------------------------------------------------------

    static UAsset Load(string path, Usmap map) => new UAsset(path, VER, map);

    static string ArgAfter(string[] argv, string flag)
    {
        int i = Array.IndexOf(argv, flag);
        if (i < 0 || i + 1 >= argv.Length) throw new Exception(flag + " needs a value");
        return argv[i + 1];
    }

    static void EnsureDir(string file)
    {
        var dir = Path.GetDirectoryName(Path.GetFullPath(file));
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
    }

    static string NameOf(FPackageIndex idx, UAsset a) =>
        idx.IsImport() ? idx.ToImport(a).ObjectName.ToString()
      : idx.IsExport() ? idx.ToExport(a).ObjectName.ToString() : "";

    // Name lookups refuse ambiguity rather than taking the first hit: --verify
    // re-reads through the same lookup, so a wrong pick would verify itself.
    static FunctionExport Fn(UAsset a, string name)
    {
        var hits = a.Exports.OfType<FunctionExport>().Where(x => x.ObjectName.ToString() == name).ToList();
        if (hits.Count != 1) throw new Exception($"{hits.Count} function exports named {name}; expected exactly 1");
        return hits[0];
    }

    static NormalExport Cdo(UAsset a)
    {
        var hits = a.Exports.OfType<NormalExport>().Where(x => x.ObjectName.ToString().StartsWith("Default__")).ToList();
        if (hits.Count != 1) throw new Exception($"{hits.Count} Default__ exports; expected exactly 1");
        return hits[0];
    }

    // Every Blueprint event compiles to a thunk that enters the ubergraph:
    //     [one EX_LetValueOnPersistentFrame per parameter]
    //     ExecuteUbergraph_<BP>(<offset>) ; Return ; EndOfScript
    // ReceiveTick(DeltaSeconds) is four instructions, CompleteCurrentPrompt three.
    // The offset is the only thing distinguishing one event from another, and it
    // is only trusted when the call really is into the ubergraph - a function
    // with a body of its own also has calls with integer arguments.
    static EX_IntConst? UbergraphEntry(FunctionExport fe, UAsset a)
    {
        if (fe.ScriptBytecode == null) return null;
        foreach (var e in fe.ScriptBytecode)
        {
            if (e is not EX_FinalFunction call) continue;
            if (!NameOf(call.StackNode, a).StartsWith("ExecuteUbergraph")) continue;
            foreach (var p in call.Parameters)
                if (p is EX_IntConst c) return c;
        }
        return null;
    }

    static int CountDiff(byte[] a, byte[] b)
    {
        int n = 0;
        for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) n++;
        return n;
    }

    // ---- inspection modes -------------------------------------------------------

    // Walk every .uasset under a directory and print its top-level export classes.
    // Used to derive the list of DIS scenes the blocklist can name: the identity
    // AutoQTE matches on is the level sequence's full name, so the blockable set
    // is exactly the assets carrying an InteractiveSceneLevelSequence export. A
    // package can hold several top-level exports (the sequence plus its director
    // Blueprint class), so all of them are reported - filtering on one would hide
    // the sequence behind its director.
    static int Classify(string root, Usmap map)
    {
        foreach (var f in Directory.EnumerateFiles(root, "*.uasset", SearchOption.AllDirectories).OrderBy(x => x))
        {
            string cls;
            try
            {
                var a = Load(f, map);
                var names = a.Exports
                    .Where(e => e.OuterIndex.Index == 0 && !e.ObjectName.ToString().StartsWith("Default__"))
                    .Select(e => NameOf(e.ClassIndex, a))
                    .Select(n => n == "" ? "null" : n)
                    .Distinct().OrderBy(x => x).ToList();
                cls = names.Count > 0 ? string.Join("|", names) : "?";
            }
            catch (Exception ex) { cls = "ERR " + ex.GetType().Name; }
            Console.WriteLine(cls + "\t" + Path.GetRelativePath(root, f).Replace('\\', '/'));
        }
        return 0;
    }

    // --enum <Name>: the enumerators of a usmap enum, in index order. This is
    // how "Collapsed" and the Lua edition's VIS_COLLAPSED = 1 are shown to be
    // the same value from the same mappings the pak is built with.
    static int ListEnum(string name, Usmap map)
    {
        if (!map.EnumMap.TryGetValue(name, out var e))
            throw new Exception("no enum named " + name + " in the mappings");
        // UsmapEnum's container is not part of the documented surface; take
        // whatever "Values" it exposes, keyed or plain.
        object vals = e.GetType().GetField("Values")?.GetValue(e)
                   ?? e.GetType().GetProperty("Values")?.GetValue(e)
                   ?? throw new Exception("UsmapEnum exposes no Values member");
        if (vals is System.Collections.IDictionary d)
            foreach (var k in d.Keys.Cast<object>().OrderBy(k => Convert.ToInt64(k)))
                Console.WriteLine($"   {k,3}  {d[k]}");
        else if (vals is System.Collections.IEnumerable en)
        {
            int i = 0;
            foreach (var v in en) Console.WriteLine($"   {i++,3}  {v}");
        }
        return 0;
    }

    // --list-props: every export's serialised properties, not only the class
    // default object's. Data assets (input mapping contexts, for one) keep what
    // matters on their primary export, which --list-defaults never shows.
    static int ListProps(UAsset a)
    {
        foreach (var ex in a.Exports)
        {
            if (ex is DataTableExport dt)
            {
                // A data table's rows are not properties of the export; each
                // row is its own struct. Print them the same way, by row name.
                Console.WriteLine(ex.ObjectName.ToString() + ": (data table, " + dt.Table.Data.Count + " rows)");
                foreach (var row in dt.Table.Data)
                {
                    Console.WriteLine("   [" + row.Name.ToString() + "]");
                    Show(row.Value, 6);
                }
                continue;
            }
            if (ex is not NormalExport ne) continue;
            Console.WriteLine(ex.ObjectName.ToString() + ":");
            Show(ne.Data, 3);
        }
        return 0;
    }

    static int ListImports(UAsset a)
    {
        foreach (var im in a.Imports)
            Console.WriteLine($"   {im.ClassName.ToString(),-26} {im.ObjectName.ToString(),-44} {im.ClassPackage.ToString()}");
        return 0;
    }

    static int ListFunctions(UAsset a)
    {
        foreach (var fe in a.Exports.OfType<FunctionExport>())
        {
            var entry = UbergraphEntry(fe, a);
            string off = entry != null ? entry.Value.ToString() : "-";
            Console.WriteLine($"   {fe.ObjectName.ToString(),-46} ubergraph={off,-8} instr={fe.ScriptBytecode?.Length ?? -1}");
        }
        return 0;
    }

    // Structs nest, and the interesting numbers (input windows, trigger times)
    // live inside them, so a flat dump would hide exactly what is worth finding.
    static int ListDefaults(UAsset a)
    {
        foreach (var ex in a.Exports)
        {
            if (!ex.ObjectName.ToString().StartsWith("Default__")) continue;
            Console.WriteLine(ex.ObjectName.ToString() + ":");
            if (ex is NormalExport ne) Show(ne.Data, 3);
        }
        return 0;
    }

    static void Show(IList<PropertyData> data, int indent)
    {
        string pad = new string(' ', indent);
        foreach (var pd in data)
        {
            // PropertyData subclasses share no base for Value; reflection is the
            // one honest way to print "whatever this property holds".
            object? v = pd.GetType().GetProperty("Value")?.GetValue(pd);
            if (v is IList<PropertyData> kids)
            {
                Console.WriteLine($"{pad}{pd.PropertyType.ToString(),-18} {pd.Name.ToString()}");
                Show(kids, indent + 3);
            }
            else
            {
                Console.WriteLine($"{pad}{pd.PropertyType.ToString(),-18} {pd.Name.ToString(),-40} {v}");
            }
        }
    }

    // ---- edit modes ----------------------------------------------------------------

    // Re-serialise with no edits and require the bytes back exactly. If this ever
    // fails, the library has stopped understanding some part of the asset and no
    // edit of it can be trusted.
    static int RoundTrip(UAsset asset, string src, string dst)
    {
        EnsureDir(dst);
        asset.Write(dst);
        bool allSame = true;
        foreach (var ext in new[] { ".uasset", ".uexp" })
        {
            var A = File.ReadAllBytes(Path.ChangeExtension(src, ext));
            var B = File.ReadAllBytes(Path.ChangeExtension(dst, ext));
            bool same = A.Length == B.Length && CountDiff(A, B) == 0;
            Console.WriteLine($"   {ext,-8} {A.Length} -> {B.Length}  {(same ? "IDENTICAL" : "DIFFERS")}");
            allSame &= same;
        }
        if (allSame) return 0;
        // Do not leave an output that looks like a successful round-trip.
        foreach (var ext in new[] { ".uasset", ".uexp" }) File.Delete(Path.ChangeExtension(dst, ext));
        throw new Exception("round-trip is not lossless; refusing to patch");
    }

    // --set-double / --set-enum edit one property each on the class default
    // object. A data-only change carries none of the bytecode risk, which also
    // makes it usable as a mount probe: read the value back at runtime and you
    // know whether the container loaded, independently of whether it does
    // anything useful. Every edit is re-read from the written file: a value that
    // silently does not serialise looks exactly like a mod that does nothing.
    readonly record struct Spec(bool IsEnum, string Name, string Value);

    static List<Spec> ParseSpecs(string[] argv)
    {
        var specs = new List<Spec>();
        foreach (var arg in argv)
        {
            bool isEnum = arg.StartsWith("--set-enum=");
            if (!isEnum && !arg.StartsWith("--set-double=")) continue;
            // the flag ends at the first '=', the name at the last ':' - so a
            // value may contain '=' and a name may contain ':', not the reverse
            string kv = arg.Substring(arg.IndexOf('=') + 1);
            int c = kv.LastIndexOf(':');
            if (c <= 0) throw new Exception(arg + ": expected Name:Value");
            specs.Add(new Spec(isEnum, kv.Substring(0, c), kv.Substring(c + 1)));
        }
        return specs;
    }

    static T Prop<T>(NormalExport cdo, string name) where T : PropertyData =>
        cdo.Data.OfType<T>().FirstOrDefault(x => x.Name.ToString() == name)
        ?? throw new Exception($"no {typeof(T).Name.Replace("PropertyData", "Property")} named {name}");

    static string Inv(double d) => d.ToString(CultureInfo.InvariantCulture);

    static int EditDefaults(UAsset asset, string dst, Usmap map, string[] argv)
    {
        var specs = ParseSpecs(argv);
        var cdo = Cdo(asset);
        foreach (var s in specs.Where(s => !s.IsEnum))
        {
            var pd = Prop<DoublePropertyData>(cdo, s.Name);
            double val = double.Parse(s.Value, CultureInfo.InvariantCulture);
            Console.WriteLine($"  {s.Name}: {Inv(pd.Value)} -> {Inv(val)}");
            pd.Value = val;
        }
        foreach (var s in specs.Where(s => s.IsEnum))
        {
            var pd = Prop<EnumPropertyData>(cdo, s.Name);
            Console.WriteLine($"  {s.Name}: {pd.Value.ToString()} -> {s.Value}");
            pd.Value = FName.FromString(asset, s.Value);
        }
        EnsureDir(dst);
        asset.Write(dst);

        var back = Cdo(Load(dst, map));
        foreach (var s in specs)
        {
            if (s.IsEnum)
            {
                string got = Prop<EnumPropertyData>(back, s.Name).Value.ToString();
                if (got != s.Value) throw new Exception($"verify failed: {s.Name} reads {got}, expected {s.Value}");
            }
            else
            {
                double got = Prop<DoublePropertyData>(back, s.Name).Value;
                double want = double.Parse(s.Value, CultureInfo.InvariantCulture);
                if (Math.Abs(got - want) > 1e-9) throw new Exception($"verify failed: {s.Name} reads {got}, expected {want}");
            }
        }
        Console.WriteLine("  verify OK");
        Console.WriteLine("  wrote " + dst);
        return 0;
    }

    static int PatchThunk(UAsset asset, string src, string dst, Usmap map, string from, string to, bool verify)
    {
        var entry = UbergraphEntry(Fn(asset, from), asset)
            ?? throw new Exception(from + ": no ubergraph entry - is it still a Blueprint event?");
        int fromOff = entry.Value;
        int toOff = (UbergraphEntry(Fn(asset, to), asset)
            ?? throw new Exception(to + ": no ubergraph entry - is it still a Blueprint event?")).Value;

        Console.WriteLine($"  {from,-24} -> ubergraph offset {fromOff}");
        Console.WriteLine($"  {to,-24} -> ubergraph offset {toOff}");
        if (fromOff == toOff)
        {
            Console.Error.WriteLine("  already patched, or the two events share an offset; refusing");
            return 1;
        }

        entry.Value = toOff;
        EnsureDir(dst);
        asset.Write(dst);
        Console.WriteLine($"  patched: {from} now enters the ubergraph at {toOff}");
        Console.WriteLine($"  wrote {dst}");
        if (!verify) return 0;

        var back = Load(dst, map);
        int got = (UbergraphEntry(Fn(back, from), back) ?? throw new Exception("verify failed: entry vanished")).Value;
        if (got != toOff) throw new Exception($"verify failed: re-read offset is {got}, expected {toOff}");

        // Everything but that one integer must be untouched, so compare against a
        // clean re-serialisation of the stock asset rather than the original file.
        // .uasset may not change at all. In .uexp every differing byte must lie
        // inside one little-endian int32 that reads fromOff before and toOff
        // after - the offset literal itself - so a change anywhere else fails
        // even if it happens to be small.
        string tmp = Path.Combine(Path.GetTempPath(), "AutoQTE_pak_" + Guid.NewGuid().ToString("N") + ".uasset");
        try
        {
            Load(src, map).Write(tmp);
            foreach (var ext in new[] { ".uasset", ".uexp" })
            {
                var A = File.ReadAllBytes(Path.ChangeExtension(tmp, ext));
                var B = File.ReadAllBytes(Path.ChangeExtension(dst, ext));
                if (A.Length != B.Length)
                    throw new Exception($"verify failed: {ext} length {A.Length} -> {B.Length}");
                var d = Enumerable.Range(0, A.Length).Where(i => A[i] != B[i]).ToList();
                Console.WriteLine($"  {ext,-8} bytes differing from stock: {d.Count}");
                if (ext == ".uasset" && d.Count != 0)
                    throw new Exception("verify failed: .uasset changed, only .uexp may");
                if (ext == ".uexp")
                {
                    if (d.Count == 0) throw new Exception("verify failed: nothing changed in .uexp");
                    bool located = false;
                    for (int w = Math.Max(0, d[0] - 3); w <= d[0] && w + 4 <= A.Length; w++)
                        if (BitConverter.ToInt32(A, w) == fromOff && BitConverter.ToInt32(B, w) == toOff
                            && d.All(i => i >= w && i < w + 4))
                        { located = true; Console.WriteLine($"  .uexp    offset literal at 0x{w:X}"); break; }
                    if (!located)
                        throw new Exception("verify failed: the changed bytes are not the ubergraph offset literal");
                }
            }
        }
        finally
        {
            // never let a locked temp file replace the real exception
            try { foreach (var ext in new[] { ".uasset", ".uexp" }) File.Delete(Path.ChangeExtension(tmp, ext)); }
            catch { }
        }
        Console.WriteLine("  verify OK");
        return 0;
    }
}
