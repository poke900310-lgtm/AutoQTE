#!/usr/bin/env python3
"""Check whether another mod can conflict with AutoQTE.

    python tools/check_conflict.py <mod.zip | mod-folder> [...]

AutoQTE touches exactly four things, so only four questions matter:

  1. Does it hook the same UFunctions?          -> mutually exclusive
  2. Does it write the DIS prompt widget?       -> shared widget, needs a note
  3. Does it bind F4 or F5?                     -> load-order dependent
  4. Does it ship a shared UE4SS file?          -> prerequisite conflict

Anything else - textures, meshes, paks, gameplay tuning, other Lua mods that
stay off those four - cannot conflict at any load order.

Point this at what a user actually INSTALLS: the release .zip, or the package/
directory inside a source tree. Scanning a whole source checkout produces false
positives, because mod repos often vendor a copy of another mod for reference -
Controller Tweaks keeps upstream/HUDTweaks/main.lua, which trips the widget
check even though nothing in its own release touches that widget.
"""
import os
import re
import sys
import zipfile

HOOKS = ("InteractiveSceneObject", "DISLevelSequenceDirector",
         "OnInteractiveScenePlaybackStarted", "OnCompletedInteractiveSceneNotification",
         "OnCancelledInteractiveSceneNotification", "TriggerDISInteraction",
         "CompleteCurrentPrompt")
# BP_DIS as its own token: not the W of WBP_DIS_Prompt_New_C
HOOK_RE = re.compile(r"(?<![A-Za-z])BP_DIS(?![A-Za-z])")
WIDGET = ("WBP_DIS_Prompt_New", "SetRenderOpacity")
SHARED = ("mods.txt", "ue4ss-settings.ini", "dwmapi.dll", "ue4ss.dll")
OURKEYS = ("F4", "F5")
TEXT_EXT = (".lua", ".ini", ".txt", ".json", ".cfg")


def read_members(target):
    """Yield (name, bytes) for every file in a zip or a directory."""
    if os.path.isdir(target):
        for root, _, files in os.walk(target):
            for f in files:
                p = os.path.join(root, f)
                yield os.path.relpath(p, target).replace("\\", "/"), open(p, "rb").read()
    else:
        with zipfile.ZipFile(target) as z:
            for i in z.infolist():
                if not i.is_dir():
                    yield i.filename, z.read(i.filename)


def check(target):
    name = os.path.basename(target.rstrip("/\\"))
    if name in ("package", "Data", "Scripts", ""):   # uninformative wrapper dirs
        name = os.path.join(os.path.basename(os.path.dirname(target.rstrip("/\\"))), name)
    print("=" * 72)
    print(name)
    print("=" * 72)

    hooks, widget, keys, shared, kinds = set(), set(), set(), set(), {}
    for member, data in read_members(target):
        low = member.lower()
        ext = os.path.splitext(low)[1]
        kinds[ext or "(none)"] = kinds.get(ext or "(none)", 0) + 1
        for s in SHARED:
            if low.endswith(s):
                shared.add(os.path.basename(member))
        if ext not in TEXT_EXT:
            continue
        try:
            text = data.decode("utf-8", "replace")
        except Exception:
            continue
        for token in HOOKS:
            if token in text:
                hooks.add(token)
        if HOOK_RE.search(text):
            hooks.add("BP_DIS")
        for token in WIDGET:
            if token in text:
                widget.add(token)
        for m in re.finditer(r"Key\.([A-Z_0-9]+)", text):
            if m.group(1) in OURKEYS:
                keys.add(m.group(1))
        for m in re.finditer(r'["\'](F[0-9]{1,2})["\']', text):
            if m.group(1) in OURKEYS:
                keys.add(m.group(1))

    print("  ships: " + ", ".join("%s x%d" % (k, v) for k, v in sorted(kinds.items())))

    verdict = "COMPATIBLE"
    if shared:
        print("  [!] SHARED UE4SS FILES: " + ", ".join(sorted(shared)))
        print("      Prerequisite conflict - installing this may replace your UE4SS")
        print("      config or load order. Not an AutoQTE conflict; pick one package.")
        verdict = "REVIEW"
    if hooks:
        print("  [!] TOUCHES THE DIS SYSTEM: " + ", ".join(sorted(hooks)))
        print("      Likely mutually exclusive with AutoQTE. Run one or the other.")
        verdict = "CONFLICT"
    if widget:
        print("  [!] WRITES HUD WIDGET PROPERTIES: " + ", ".join(sorted(widget)))
        print("      May contend for the DIS prompt widget. AutoQTE will not")
        print("      overwrite another mod's value; if the prompt is ever left")
        print("      faded, set DIS.HidePrompt = false.")
        if verdict == "COMPATIBLE":
            verdict = "NOTE"
    if keys:
        print("  [!] MAY BIND " + ", ".join(sorted(keys)) + " - AutoQTE's default keys.")
        print("      AutoQTE yields to whoever registered first; a mod loading")
        print("      later can co-bind. Change Config.Keys if a key does nothing.")
        if verdict == "COMPATIBLE":
            verdict = "NOTE"
    if verdict == "COMPATIBLE":
        print("  nothing in common with AutoQTE - no conflict at any load order")
    print("  VERDICT: " + verdict)
    print()
    return verdict


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for t in sys.argv[1:]:
        if not os.path.exists(t):
            print("missing: " + t)
            continue
        check(t)


if __name__ == "__main__":
    main()
