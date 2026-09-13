#!/usr/bin/env python3
r"""Derive every blockable DIS scene from the game and write BLOCKABLE-SCENES.md.

    set AUTOQTE_AES_KEY=0x...
    python tools/pak/list_dis_scenes.py --game "G:\Steam\steamapps\common\The Blood of Dawnwalker"

    python tools/pak/list_dis_scenes.py --classified path/to/classified.tsv   # skip extraction

What "blockable" means here is exact. AutoQTE identifies a scene as

    <BP_DIS actor full name> <level sequence full name>      (lowercased)

and BlockAlso matches a plain substring of that string. The level-sequence half
is the asset's package path, so the set of scenes a pattern can ever name is the
set of packages whose top-level export is an InteractiveSceneLevelSequence. The
folder they live in is not reliable - some are under DialogueInteractions/, some
under Dialogues/Cinematic/*/DIS/, one under Dialog/DIS_Sequences/ - so this
extracts by three path filters and then keeps only that class.

Needs retoc, the .usmap and the patcher, exactly like build_pak.py. The
patcher's --classify mode does the class check.

The output also cross-checks the reference set in AutoQTE.defaults.ini: every
pattern there must still match at least one real scene, or a game update has
renamed something and the shipped example is silently dead.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "BLOCKABLE-SCENES.md")
INI = os.path.join(ROOT, "AutoQTE.defaults.ini")
FILTERS = ["DialogueInteractions", "DIS/", "DIS_"]
CLASS = "InteractiveSceneLevelSequence"


def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        shown = ["<key>" if i and cmd[i - 1] == "-a" else str(c) for i, c in enumerate(cmd)]
        sys.exit("failed: %s\n%s%s" % (" ".join(shown), p.stdout[-2000:], p.stderr[-2000:]))
    return p.stdout


def find_usmap(given):
    if given:
        return given
    import glob
    hits = glob.glob(os.path.join(ROOT, "tools", "bin", "*.usmap"))
    if not hits:
        sys.exit("no .usmap in tools/bin - see tools/pak/README.md")
    chosen = max(hits, key=os.path.getmtime)
    print("  usmap: %s" % os.path.basename(chosen))
    return chosen


def classify(game, retoc, usmap, key, work):
    import shutil
    paks = os.path.join(game, "Dawnwalker", "Content", "Paks")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    if not key:
        sys.exit("the game's containers are encrypted: pass --aes-key or set AUTOQTE_AES_KEY")
    for f in FILTERS:
        out = run([retoc, "-a", key, "to-legacy", "--version", "UE5_5", "--filter", f, paks, work])
        m = re.search(r"Extracted (\d+)", out)
        print("  filter %-22s %s assets" % (f, m.group(1) if m else "?"))
    return run(["dotnet", "run", "--project", os.path.join(ROOT, "tools", "pak", "patcher"),
                "--", "x", usmap, "x", "--classify", work], cwd=ROOT)


def reference_patterns():
    """The commented BlockAlso example line in the defaults ini."""
    body = open(INI, encoding="utf-8").read()
    m = re.search(r"^;\s*BlockAlso\s*=\s*(.+)$", body, re.M)
    if not m:
        return []
    return [p.strip().lower() for p in m.group(1).split(",") if p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game")
    ap.add_argument("--retoc", default="retoc.exe")
    ap.add_argument("--usmap")
    ap.add_argument("--aes-key", default=os.environ.get("AUTOQTE_AES_KEY"))
    ap.add_argument("--classified", help="an existing --classify listing; skips extraction")
    ap.add_argument("--work", default=os.path.join(ROOT, "dist", "_dis"))
    a = ap.parse_args()

    if a.classified:
        tsv = open(a.classified, encoding="utf-8").read()
    else:
        if not a.game:
            sys.exit("--game is required unless --classified is given")
        tsv = classify(a.game, a.retoc, find_usmap(a.usmap), a.aes_key, a.work)

    scenes = []
    for line in tsv.splitlines():
        if "\t" not in line:
            continue
        cls, path = line.split("\t", 1)
        if CLASS not in cls.split("|"):
            continue
        path = path.replace("\\", "/")
        path = re.sub(r"^Dawnwalker/Content/", "", path)
        path = re.sub(r"\.uasset$", "", path)
        scenes.append(path)
    # A row the classifier could not parse would otherwise vanish exactly like
    # an irrelevant asset, and the list is documented as complete.
    errs = [l.split("\t", 1)[1] for l in tsv.splitlines() if l.startswith("ERR ")]
    if errs:
        sys.exit("%d asset(s) failed to classify and would be missing from the list:\n  %s"
                 % (len(errs), "\n  ".join(errs[:20])))
    scenes.sort(key=str.lower)
    if not scenes:
        sys.exit("no %s assets found - did the class get renamed?" % CLASS)

    # The identity half a pattern is matched against: /game/<path> lowercased.
    ids = {s: ("/game/" + s).lower() for s in scenes}
    names = {s: s.rsplit("/", 1)[-1].lower() for s in scenes}

    # Cross-check the shipped reference set against reality.
    ref = reference_patterns()
    dead = [p for p in ref if not any(p in i for i in ids.values())]
    hits = {p: [s for s in scenes if p in ids[s]] for p in ref}

    # A basename that is a substring of another basename blocks both. Say so.
    overlaps = {}
    for s in scenes:
        n = names[s]
        others = [t for t in scenes if t != s and n in ids[t]]
        if others:
            overlaps[s] = others

    lines = []
    w = lines.append
    w("# Blockable DIS scenes")
    w("")
    w("Every scene AutoQTE can be told to leave alone, derived from the game's own")
    w("containers by asset class (`%s`), not by folder or name." % CLASS)
    w("Regenerate after a game patch with `tools/pak/list_dis_scenes.py`; do not edit")
    w("by hand.")
    w("")
    w("**%d scenes.** `BlockAlso` matches a lowercase substring of the scene identity," % len(scenes))
    w("and the identity ends in the package path below, so the safe pattern for a")
    w("scene is its lowercased file name. Several patterns go on one `BlockAlso` line")
    w("separated by commas, or on several `BlockAlso` lines - both accumulate. A")
    w("single value must not be wrapped across lines; the parser reads one key per")
    w("line and a wrapped value applies only its first line.")
    w("")
    w("## Reference set in `AutoQTE.defaults.ini`")
    w("")
    if dead:
        w("**BROKEN: %s match nothing.** A game update renamed these; fix the ini." % ", ".join("`%s`" % p for p in dead))
        w("")
    w("| pattern | scenes it blocks |")
    w("|---|---|")
    for p in ref:
        w("| `%s` | %s |" % (p, ", ".join("`%s`" % names[s] for s in hits[p]) or "**nothing**"))
    w("")
    w("## All scenes, by quest")
    w("")
    w("| pattern (file name) | package |")
    w("|---|---|")
    last = None
    for s in scenes:
        parts = s.split("/")
        quest = parts[2] if len(parts) > 2 and parts[1] == "Quest" else (parts[1] if len(parts) > 1 else parts[0])
        if quest != last:
            w("| **%s** | |" % quest)
            last = quest
        note = ""
        if s in overlaps:
            note = " - also matches " + ", ".join("`%s`" % names[t] for t in overlaps[s])
        w("| `%s`%s | `%s` |" % (names[s], note, s))
    w("")
    w("## Choosing a pattern")
    w("")
    w("Longer is safer. `dis_shelf` also matches `q302_dis_shelf` and `q303_dis_shelf`;")
    w("`sq711_chopping_wood` matches all four of that quest's chopping scenes. If you")
    w("mean one scene, use its whole file name. If you mean the family, the shared")
    w("stem is the point. Press F5 during a scene to see its exact identity.")
    w("")
    open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("wrote %s: %d scenes, %d reference patterns%s"
          % (os.path.relpath(OUT, ROOT), len(scenes), len(ref),
             ", %d DEAD" % len(dead) if dead else ", all matching"))
    if dead:
        sys.exit(1)


if __name__ == "__main__":
    main()
