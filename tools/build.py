#!/usr/bin/env python3
r"""Build AutoQTE.zip in the layout Vortex's "UE4SS (Lua mods)" type expects.

    python tools/build.py            -> dist/AutoQTE.zip

Data/ is what gets deployed into ue4ss\Mods\; README.txt and LICENSE.txt sit
at the archive root so they stay out of the game folder. Forward slashes only,
no directory entries, no stray files.
"""
import hashlib
import os
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "dist", "AutoQTE.zip")

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

    src = os.path.join(ROOT, "Scripts", "main.lua")
    text = open(src, encoding="utf-8").read()
    for flag in ("Verbose = true", "LogEveryCompletion = true"):
        if flag in text:
            sys.exit("refusing to ship with %s - reset it in Scripts/main.lua" % flag)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, rel in ENTRIES:
            path = os.path.join(ROOT, rel)
            info = zipfile.ZipInfo(arc, date_time=time.localtime(os.path.getmtime(path))[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, open(path, "rb").read())

    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None, "archive failed its integrity check"
        print(OUT)
        for i in z.infolist():
            digest = hashlib.md5(z.read(i.filename)).hexdigest()
            print("  %8d  %-32s %s" % (i.file_size, i.filename, digest))


if __name__ == "__main__":
    main()
