#!/usr/bin/env python3
r"""Package the built .pak edition for release.

    python tools/pak/build_archive.py            -> dist/AutoQTE-PAK-<version>.zip

Run tools/pak/build_pak.py first; this only packages what that produced.

Same layout rule as the UE4SS edition: the full path from the game folder, so
one archive serves both routes - extract it into the game folder and it merges
into place, and a mod manager deploying relative to the game root lands the
same files in the same spots.

The readme goes next to the containers rather than at the archive root. A root
file would be dropped loose into the game folder by a manual extract, and would
not be removed when the mod is. Naming it after the containers keeps it
obviously part of this mod and obviously deletable.

Versioning is independent of the UE4SS edition. The two ship different code and
change for different reasons, so a shared number would claim a parity that does
not exist - a Lua-only fix must not appear to be a new pak.
"""
import hashlib
import os
import sys
import time
import zipfile

VERSION = "1.0.1"

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIST = os.path.join(ROOT, "dist")
PAKPATH = "Dawnwalker/Content/Paks/"
CONTAINERS = ["AutoQTE_P.pak", "AutoQTE_P.ucas", "AutoQTE_P.utoc"]

README = """AutoQTE - .pak edition %s

Auto-completes the quick-time prompts in Dialogue Interaction Scenes. This
edition needs no UE4SS: it is an asset override the engine loads on its own.

INSTALL
  Copy the Dawnwalker folder in this archive into your game folder, so the
  three AutoQTE_P files end up in:

    <game>\\Dawnwalker\\Content\\Paks\\

  Or install the archive with a mod manager.

UNINSTALL
  Delete AutoQTE_P.pak, AutoQTE_P.ucas, AutoQTE_P.utoc and this readme.
  Nothing else is touched and nothing is written to your save.

WHICH EDITION
  The UE4SS edition has a toggle key, a diagnose key, a per-scene blocklist and
  a log. This one has none of those - it is all-or-nothing auto-complete, and
  that is the trade for not needing UE4SS. Install one or the other, not both.

WHAT IT CHANGES
  Two assets. BP_DIS completes a prompt as soon as one starts, and the prompt
  widget is set not to draw. It does not touch combat: Voracious Bite and blood
  drinking run through a different system entirely.

A GAME PATCH MAY BREAK IT
  It overrides two cooked assets from a specific game build. After a game
  update, remove it if anything behaves oddly, and watch the mod page for a
  rebuild.

SAVE OFTEN
  Completing a scene is a real outcome the game records. Keep your own saves.
""" % VERSION


def main():
    missing = [c for c in CONTAINERS if not os.path.isfile(os.path.join(DIST, c))]
    if missing:
        sys.exit("missing %s in dist/ - run tools/pak/build_pak.py first"
                 % ", ".join(missing))

    out = os.path.join(DIST, "AutoQTE-PAK-%s.zip" % VERSION)
    # Drop older pak archives so the directory never offers two answers to
    # "which one do I upload".
    for f in os.listdir(DIST):
        if f.startswith("AutoQTE-PAK-") and f.endswith(".zip") and f != os.path.basename(out):
            os.remove(os.path.join(DIST, f))
            print("removed stale %s" % f)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for c in CONTAINERS:
            src = os.path.join(DIST, c)
            info = zipfile.ZipInfo(PAKPATH + c,
                                   date_time=time.localtime(os.path.getmtime(src))[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(src, "rb") as fh:
                z.writestr(info, fh.read())
        info = zipfile.ZipInfo(PAKPATH + "AutoQTE_P.README.txt", date_time=time.localtime()[:6])
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, README.replace("\n", "\r\n").encode("utf-8"))

    with zipfile.ZipFile(out) as z:
        bad = z.testzip()
        if bad:
            sys.exit("archive is corrupt at " + bad)
        names = z.namelist()
    blob = open(out, "rb").read()
    print("%s  %d bytes" % (os.path.relpath(out, ROOT), len(blob)))
    print("md5 %s" % hashlib.md5(blob).hexdigest())
    for n in names:
        print("   " + n)


if __name__ == "__main__":
    main()
