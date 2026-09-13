#!/usr/bin/env python3
r"""Build the release archive in the layout a mod manager's "UE4SS (Lua mods)" type expects.

    python tools/build.py            -> dist/AutoQTE-<version>.zip

The archive carries the full path from the game folder
(Dawnwalker/Binaries/Win64/ue4ss/Mods/AutoQTE/), so it works both as a drop-in
extract and as a mod-manager install; README.txt and LICENSE.txt sit inside the
mod folder so an extract never drops them loose in the game directory. Forward
slashes only, no directory entries, no stray files.
"""
import glob
import hashlib
import os
import re
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = None   # set in main(), named after the version in main.lua

def version_of(path):
    m = re.search(r'^local VERSION = "([^"]+)"', open(path, encoding="utf-8").read(), re.M)
    if not m:
        raise SystemExit("cannot find VERSION in " + path)
    return m.group(1)


# Full path from the game folder, so one archive serves both routes: extract it
# into the game folder and it merges into place, and a mod manager deploying
# relative to the game root lands the same files in the same spots. This is what
# the other Dawnwalker Lua mods ship; the old Data/ prefix was a a mod manager-only
# convention that left manual installers digging a folder deeper than everyone
# else's instructions told them to.
MODPATH = "Dawnwalker/Binaries/Win64/ue4ss/Mods/AutoQTE/"
ENTRIES = [
    (MODPATH + "enabled.txt",                 "enabled.txt"),
    (MODPATH + "Scripts/main.lua",            "Scripts/main.lua"),
    (MODPATH + "Scripts/AutoQTE.defaults.ini", "AutoQTE.defaults.ini"),
    # Inside the mod folder, not the archive root: extracting into the game
    # folder would otherwise drop them loose in the game directory, and they
    # would not be removed when the mod folder is deleted.
    (MODPATH + "README.txt",                  "README.txt"),
    (MODPATH + "LICENSE.txt",                 "LICENSE.txt"),
]


def main():
    missing = [s for _, s in ENTRIES if not os.path.isfile(os.path.join(ROOT, s))]
    if missing:
        sys.exit("missing source files: " + ", ".join(missing))

    # Debug flags must be off in BOTH shipped files. AutoQTE.defaults.ini is not a
    # reference copy - main.lua reads it at runtime, so it OVERRIDES the Lua defaults.
    # Match the parsed value, not a substring: "Verbose=true" is the same setting.
    for rel in ("Scripts/main.lua", "AutoQTE.defaults.ini"):
        text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        for flag in ("Verbose", "LogEveryCompletion"):
            # Parse the value the way applyIni does: optional dis. prefix, inline
            # comment, quotes - then test every spelling toBool() accepts.
            for m in re.finditer(r"^\s*(?:DIS\.)?%s\s*=\s*(.*)$" % flag, text, re.M | re.I):
                val = re.sub(r"\s+[;#].*$", "", m.group(1)).strip().strip(";#").strip()
                val = val.strip('"').strip("'").strip().lower()
                if val in ("true", "1", "yes", "on"):
                    sys.exit("refusing to ship with %s enabled in %s" % (flag, rel))

    version = version_of(os.path.join(ROOT, "Scripts", "main.lua"))
    for rel in ("README.md", "README.txt"):
        doc = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        stale = {v for v in re.findall(r"AutoQTE v?(\d+\.\d+\.\d+)", doc)} - {version}
        if version not in doc:
            sys.exit("%s never mentions version %s" % (rel, version))
        if stale:
            sys.exit("%s still mentions version(s) %s; main.lua says %s"
                     % (rel, ", ".join(sorted(stale)), version))

    # a mod manager reads a mod's version from the archive filename, so put it there.
    global OUT
    OUT = os.path.join(ROOT, "dist", "AutoQTE-%s.zip" % version)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)

    # Only one archive may sit in dist/. Attaching last release's zip to a new
    # tag is a mistake you cannot take back once anyone has downloaded it.
    # The .pak edition is versioned separately and builds into the same
    # directory; its archive is not a stale copy of this one.
    for stale_zip in glob.glob(os.path.join(ROOT, "dist", "AutoQTE-*.zip")):
        if "-PAK-" in os.path.basename(stale_zip):
            continue
        if os.path.abspath(stale_zip) != os.path.abspath(OUT):
            os.remove(stale_zip)
            print("removed stale %s" % os.path.basename(stale_zip))

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, rel in ENTRIES:
            path = os.path.join(ROOT, rel)
            info = zipfile.ZipInfo(arc, date_time=time.localtime(os.path.getmtime(path))[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, open(path, "rb").read())

    with zipfile.ZipFile(OUT) as z:
        if z.testzip() is not None:
            raise SystemExit("archive failed its integrity check")
        print(OUT)
        for i in z.infolist():
            digest = hashlib.md5(z.read(i.filename)).hexdigest()
            print("  %8d  %-32s %s" % (i.file_size, i.filename, digest))


if __name__ == "__main__":
    main()
