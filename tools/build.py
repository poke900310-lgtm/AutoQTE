#!/usr/bin/env python3
r"""Build the release archive in the layout Vortex's "UE4SS (Lua mods)" type expects.

    python tools/build.py            -> dist/AutoQTE-<version>.zip

Data/ is what gets deployed into ue4ss\Mods\; README.txt and LICENSE.txt sit
at the archive root so they stay out of the game folder. Forward slashes only,
no directory entries, no stray files.
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


ENTRIES = [
    ("Data/AutoQTE/enabled.txt",      "enabled.txt"),
    ("Data/AutoQTE/Scripts/main.lua", "Scripts/main.lua"),
    ("Data/AutoQTE/Scripts/AutoQTE.defaults.ini", "AutoQTE.defaults.ini"),
    ("README.txt",                    "README.txt"),
    ("LICENSE.txt",                   "LICENSE.txt"),
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

    # Vortex reads a mod's version from the archive filename, so put it there.
    global OUT
    OUT = os.path.join(ROOT, "dist", "AutoQTE-%s.zip" % version)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)

    # Only one archive may sit in dist/. Attaching last release's zip to a new
    # tag is a mistake you cannot take back once anyone has downloaded it.
    for stale_zip in glob.glob(os.path.join(ROOT, "dist", "AutoQTE-*.zip")):
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
