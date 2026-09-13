#!/usr/bin/env python3
r"""Build the .pak edition of AutoQTE end to end.

    python tools/pak/build_pak.py --game "G:\Steam\steamapps\common\The Blood of Dawnwalker"

Needs, once, on PATH or passed with a flag:
  * retoc.exe        https://github.com/trumank/retoc   (extract + repack IoStore)
  * dotnet SDK       to run tools/pak/patcher
  * a .usmap         dumped from the running game; see tools/pak/README.md

Nothing here hardcodes a bytecode offset. The patcher reads both offsets out of
the asset by function name every run, so after a game patch recompiles BP_DIS
this same command still produces a correct mod. That is the entire point.

Two assets, two different kinds of edit:

  BP_DIS               ReceiveTick -> CompleteCurrentPrompt   (2 bytes of .uexp)
  WBP_DIS_Prompt_New   Visibility  -> Collapsed               (one enum)

The first completes the prompt, the second stops it being drawn. Completing a
prompt does not take its widget down - that is why both are needed, and why a
build with only the first looks like it half works.

Why Tick: a Blueprint event compiles to a thunk, but a call from inside the same
Blueprint does not go through it - the compiler emits a direct jump into the
ubergraph. So redirecting a thunk only affects callers OUTSIDE the Blueprint.
StartCurrentPrompt has none, which is why redirecting it did nothing in game.
ReceiveTick is invoked natively by the engine through ProcessEvent, and BP_DIS
only ticks while a prompt is running, so the redirect fires exactly then.

Stages, each verified before the next begins:
  1. extract both assets from the game's containers (Zen -> legacy)
  2. round-trip each unchanged and require byte-identical output
  3. patch, then re-read the result and confirm the edit is really there
  4. repack to IoStore (legacy -> Zen) and verify the container
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTENT = "Dawnwalker/Content/_Dawnwalker/"

# (name for retoc's filter, path inside the container, patcher arguments)
TARGETS = [
    ("BP_DIS",
     CONTENT + "WorldActors/DIS_Sequences/BP_DIS",
     ["--from", "ReceiveTick", "--to", "CompleteCurrentPrompt", "--verify"]),
    ("WBP_DIS_Prompt_New",
     CONTENT + "UI/_Unified/Gameplay/DIS/WBP_DIS_Prompt_New",
     ["--set-enum=Visibility:Collapsed"]),
]


def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        # never echo the AES key: a pasted failure report must not publish it
        shown = ["<key>" if i and cmd[i - 1] == "-a" else str(c) for i, c in enumerate(cmd)]
        sys.exit("failed: %s\n%s%s" % (" ".join(shown), p.stdout[-2000:], p.stderr[-2000:]))
    return p.stdout


def patcher(args, cwd):
    return run(["dotnet", "run", "--project", os.path.join(ROOT, "tools", "pak", "patcher"), "--"]
               + list(args), cwd=cwd)


def find_usmap(game, given):
    if given:
        return given
    # tools/bin is gitignored and survives UE4SS being uninstalled from the
    # game, which is the normal state once the pak edition is what is being
    # played. A mappings file that only lives beside UE4SS.dll is deleted with
    # it, and this build then cannot run at all.
    for pat in (os.path.join(ROOT, "tools", "bin", "*.usmap"),
                os.path.join(game, "Dawnwalker", "Binaries", "Win64", "ue4ss", "*.usmap")):
        hits = glob.glob(pat)
        if hits:
            return max(hits, key=os.path.getmtime)   # newest, not last by name
    sys.exit("no .usmap in tools/bin or beside UE4SS.dll. Dump one first - see tools/pak/README.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True, help="the folder containing Dawnwalker")
    ap.add_argument("--retoc", default="retoc.exe")
    ap.add_argument("--usmap", default=None)
    # The game's containers are AES-encrypted. The key is NOT stored in this
    # repository and must not be: publishing a commercial game's decryption key
    # is a different act from publishing a mod. Pass it per build, or set
    # AUTOQTE_AES_KEY in the environment.
    ap.add_argument("--aes-key", default=os.environ.get("AUTOQTE_AES_KEY"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--work", default=os.path.join(ROOT, "dist", "_pak"))
    a = ap.parse_args()

    usmap = find_usmap(a.game, a.usmap)
    paks = os.path.join(a.game, "Dawnwalker", "Content", "Paks")
    work = a.work
    shutil.rmtree(work, ignore_errors=True)
    raw, stage = os.path.join(work, "raw"), os.path.join(work, "stage")
    os.makedirs(raw, exist_ok=True)

    print("game   : %s" % a.game)
    print("usmap  : %s" % os.path.basename(usmap))

    # 1. extract -------------------------------------------------------------
    # Pass the Paks DIRECTORY, not one .utoc: retoc needs global.utoc alongside
    # the game container to resolve package names, and without it a name filter
    # silently matches nothing and extracts zero files without failing.
    if not os.path.exists(os.path.join(paks, "Dawnwalker-Windows.utoc")):
        sys.exit("no Dawnwalker-Windows.utoc under %s" % paks)
    if not a.aes_key:
        sys.exit("the game's containers are encrypted: pass --aes-key or set AUTOQTE_AES_KEY")
    # Extraction reads the Paks directory as the game sees it, mod containers
    # included - so building while a previous AutoQTE_P is installed extracts
    # the ALREADY PATCHED asset and the patcher then refuses it as "already
    # patched". Rebuilding after a game update is exactly when the old mod is
    # still sitting there, so this is worth catching by name rather than by
    # symptom.
    # Exact stock names, recursively: a prefix test would wave through a mod
    # shipped as Dawnwalker-Windows_P.* - the standard UE mod name - and a flat
    # listing would miss a subfolder.
    STOCK = {"dawnwalker-windows.utoc", "dawnwalker-windows.ucas", "dawnwalker-windows.pak",
             "global.utoc", "global.ucas"}
    strays = sorted(os.path.relpath(os.path.join(d, f), paks)
                    for d, _, fs in os.walk(paks) for f in fs
                    if f.lower().endswith((".utoc", ".pak", ".ucas")) and f.lower() not in STOCK)
    if strays:
        sys.exit("mod containers are installed in %s:\n  %s\n"
                 "Move them out before building - otherwise the build extracts them\n"
                 "instead of the stock assets." % (paks, "\n  ".join(strays)))

    print("\n1. extracting")
    for name, path, _ in TARGETS:
        run([a.retoc, "-a", a.aes_key, "to-legacy", "--version", "UE5_5",
             "--filter", name, paks, raw])
        src = os.path.join(raw, path + ".uasset")
        if not os.path.exists(src):
            sys.exit("extraction produced no %s - did the asset move?" % path)
        print("   %-22s %d bytes" % (name, os.path.getsize(src)))

    # 2. prove the round-trip is lossless before trusting any edit -----------
    print("\n2. no-op round-trip must be byte-identical")
    for name, path, _ in TARGETS:
        print("   " + name)
        out = patcher([os.path.join(raw, path + ".uasset"), usmap,
                       os.path.join(work, "roundtrip", name + ".uasset"),
                       "--roundtrip-only"], ROOT)
        print("".join("   " + l + "\n" for l in out.strip().splitlines()))

    # 3. patch ---------------------------------------------------------------
    print("3. patching")
    for name, path, args in TARGETS:
        print("   " + name)
        out = patcher([os.path.join(raw, path + ".uasset"), usmap,
                       os.path.join(stage, path + ".uasset")] + args, ROOT)
        print("".join("   " + l + "\n" for l in out.strip().splitlines()))

    # 4. repack --------------------------------------------------------------
    print("4. repacking to IoStore")
    os.makedirs(a.out, exist_ok=True)
    target = os.path.join(a.out, "AutoQTE_P.utoc")
    for ext in (".utoc", ".ucas", ".pak"):
        stale = os.path.splitext(target)[0] + ext
        if os.path.exists(stale):
            os.remove(stale)
    run([a.retoc, "to-zen", "--version", "UE5_5", stage, target])
    print("   " + run([a.retoc, "verify", target]).strip())
    for ext in (".utoc", ".ucas", ".pak"):
        f = os.path.splitext(target)[0] + ext
        print("   %-18s %d bytes" % (os.path.basename(f), os.path.getsize(f)))

    # Content/Paks itself is where the container was verified to mount. The
    # ~mods subfolder was only ever tried with an inert patch, so it is
    # unverified rather than known not to work.
    print("\ninstall: copy the three AutoQTE_P files into")
    print(r"  <game>\Dawnwalker\Content\Paks")


if __name__ == "__main__":
    main()
