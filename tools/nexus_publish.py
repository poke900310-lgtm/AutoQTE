#!/usr/bin/env python3
r"""Publish the built archive to Nexus Mods as a new version of an existing file.

    set NEXUS_API_KEY=...                       (https://www.nexusmods.com/settings/api-keys)
    python tools/nexus_publish.py               # dry run: resolve and print the plan
    python tools/nexus_publish.py --publish     # actually upload
    python tools/nexus_publish.py --pak ...     # the .pak edition, a separate file

Nexus API v3. The flow, per the spec:

    POST /uploads                      -> upload id + presigned_url
    PUT  <presigned_url>               -> the bytes
    POST /uploads/{id}/finalise        -> close the session
    GET  /uploads/{id}                 -> poll until state == available
    POST /mod-files/{id}/versions      -> becomes the newest version of the file

Three headers on the PUT are part of the URL signature (X-Amz-SignedHeaders is
content-disposition;content-md5;content-type;host), so the upload is rejected if
any is missing or does not match: Content-Disposition (the filename sent to
/uploads), Content-MD5 (base64 of the digest, not the hex one), and Content-Type
(application/octet-stream). The last one is the trap: urllib adds
application/x-www-form-urlencoded on its own if you do not set it.

md5 is optional until 2026-12-01 and required after. It is always sent here.
"""
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.nexusmods.com/v3"
GAME = "thebloodofdawnwalker"
MOD = "456"                       # the id in the mod page URL
MOD_FILE_NAME = "AutoQTE"         # what the file should be called, version-free
PAK_FILE_NAME = "AutoQTE (.pak edition)"   # the UE4SS-free edition, a separate file
RENAME_FILE = True                # rename the target file to MOD_FILE_NAME
SET_PRIMARY = True                # make this version the default manager download
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The API enforces these; failing here beats a 422 after the bytes are uploaded.
NAME_RE = re.compile(r"^[a-zA-Z0-9 _'().-]+$")
VERSION_RE = re.compile(r"^[a-zA-Z0-9.-]+$")


def die(msg):
    raise SystemExit("nexus_publish: " + msg)


def call(method, path, key, body=None, expect=(200, 201, 204)):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("apikey", key)
    req.add_header("Accept", "application/json")
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data) as r:
            raw = r.read()
            if r.status not in expect:
                die("%s %s -> %d" % (method, path, r.status))
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        die("%s %s -> %d\n%s" % (method, path, e.code, detail))


def archive(pak):
    # Two editions now build into the same directory, so "the one archive" is no
    # longer a safe assumption: pick by edition and still require it to be
    # unambiguous within that edition.
    dist = os.path.join(ROOT, "dist")
    zips = [f for f in os.listdir(dist) if f.startswith("AutoQTE-") and f.endswith(".zip")]
    want = [f for f in zips if ("-PAK-" in f) == pak]
    if len(want) != 1:
        die("expected exactly one %s archive in dist/, found %d: %s"
            % ("pak" if pak else "UE4SS", len(want), want or zips))
    return os.path.join(dist, want[0])


def version_of(path, pak):
    # Each edition carries its own version, in the file that actually defines it.
    src_file = (os.path.join(ROOT, "tools", "pak", "build_archive.py") if pak
                else os.path.join(ROOT, "Scripts", "main.lua"))
    src = open(src_file, encoding="utf-8").read()
    m = re.search(r'VERSION = "([^"]+)"', src)
    if not m:
        die("could not read VERSION from %s" % os.path.relpath(src_file, ROOT))
    v = m.group(1)
    if v not in os.path.basename(path):
        die("archive %s does not carry version %s - rebuild first" % (os.path.basename(path), v))
    return v


def main():
    publish = "--publish" in sys.argv
    key = os.environ.get("NEXUS_API_KEY", "").strip()
    if not key:
        die("set NEXUS_API_KEY (https://www.nexusmods.com/settings/api-keys)")

    pak = "--pak" in sys.argv
    file_name = PAK_FILE_NAME if pak else MOD_FILE_NAME
    path = archive(pak)
    version = version_of(path, pak)
    blob = open(path, "rb").read()
    digest = hashlib.md5(blob).digest()
    hex_md5 = digest.hex()
    b64_md5 = base64.b64encode(digest).decode()
    filename = os.path.basename(path)

    if not NAME_RE.match(file_name) or len(file_name) > 50:
        die("mod file name %r fails the API's pattern" % file_name)
    if not VERSION_RE.match(version) or len(version) > 50:
        die("version %r fails the API's pattern" % version)

    # Resolve mod -> its files, so the new version lands on the right one.
    mod = call("GET", "/games/%s/mods/%s" % (GAME, MOD), key)["data"]
    files = call("GET", "/mods/%s/files" % mod["id"], key)["data"]["mod_files"]
    match = [f for f in files if f["name"] == file_name]
    if not match and pak:
        # The pak file was created on the site by hand under a working title
        # ("BETA - AutoQTE PAK 1.0.0 ..."). Any file with PAK in its name is
        # that one; the UE4SS files never carry it. It is renamed to the clean
        # name on publish.
        match = [f for f in files if "PAK" in f["name"]]
    if not match and not pak:
        # The page's files were once named per-version ("AutoQTE 1.0.4"), so an
        # exact match can miss. Falling back to the single active file continues
        # the update chain users already follow.
        match = [f for f in files if f.get("is_active")]
    if len(match) != 1:
        if pak:
            # No fallback here on purpose: the nearest match would be the UE4SS
            # file, and adding a pak as a version of it would push the wrong
            # download to everyone already following that file.
            die("no mod file named %r on the page. The two editions are separate\n"
                "downloads, so create that file once on the site and re-run.\n"
                "found: %s" % (file_name, [f["name"] for f in files]))
        die("could not pick a target file; found: %s"
            % [(f["name"], f.get("is_active")) for f in files])
    mod_file = match[0]

    print("  mod            %s  (%s/%s)" % (mod.get("name") or mod["id"], GAME, MOD))
    print("  mod file       %s  id=%s  versions=%s"
          % (mod_file["name"], mod_file["id"], mod_file.get("versions_count")))
    print("  archive        %s  %d bytes" % (filename, len(blob)))
    print("  version        %s" % version)
    print("  md5            %s" % hex_md5)
    if RENAME_FILE and mod_file["name"] != file_name:
        print("  will rename    %r -> %r" % (mod_file["name"], file_name))
    if not publish:
        print("\n  dry run - nothing uploaded. Re-run with --publish.")
        return

    up = call("POST", "/uploads", key, {
        "size_bytes": len(blob), "filename": filename, "md5": hex_md5})["data"]
    print("  upload         %s" % up["id"])

    put = urllib.request.Request(up["presigned_url"], method="PUT", data=blob)
    # Both of these are signed into the URL; a mismatch is rejected.
    put.add_header("Content-Disposition", 'attachment; filename="%s"' % filename)
    put.add_header("Content-MD5", b64_md5)
    # content-type is in X-Amz-SignedHeaders too, and urllib silently supplies
    # application/x-www-form-urlencoded whenever a body is present - which does
    # not match what Nexus signed, and S3 answers SignatureDoesNotMatch. Set it
    # explicitly; octet-stream is the value that verifies.
    put.add_header("Content-Type", "application/octet-stream")
    try:
        with urllib.request.urlopen(put) as r:
            print("  put            %d" % r.status)
    except urllib.error.HTTPError as e:
        die("PUT presigned_url -> %d\n%s" % (e.code, e.read().decode("utf-8", "replace")[:600]))

    call("POST", "/uploads/%s/finalise" % up["id"], key)
    for _ in range(60):
        state = call("GET", "/uploads/%s" % up["id"], key)["data"]["state"]
        if state == "available":
            break
        time.sleep(2)
    else:
        die("upload did not become available; it may still be processing")
    print("  state          available")

    made = call("POST", "/mod-files/%s/versions" % mod_file["id"], key, {
        "upload_id": up["id"],
        "name": file_name,
        "version": version,
        # The UE4SS edition is the main file and carries the mod's version; the
        # pak is an optional file with its own version and must not become the
        # default manager download or relabel the page.
        "file_category": "optional" if pak else "main",
        "update_mod_version": not pak,
        "archive_existing_file": True,
        "primary_mod_manager_download": SET_PRIMARY and not pak,
    })["data"]
    print("  version id     %s" % made["version"]["id"])
    if RENAME_FILE and mod_file["name"] != file_name:
        call("PUT", "/mod-files/%s" % mod_file["id"], key, {"name": file_name})
        print("  renamed       %r -> %r" % (mod_file["name"], file_name))
    print("\n  published %s as %s" % (filename, version))
    print("  https://www.nexusmods.com/%s/mods/%s?tab=files" % (GAME, MOD))


if __name__ == "__main__":
    main()
