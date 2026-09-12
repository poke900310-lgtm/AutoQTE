#!/usr/bin/env python3
r"""Publish the built archive to Nexus Mods as a new version of an existing file.

    set NEXUS_API_KEY=...                       (https://www.nexusmods.com/settings/api-keys)
    python tools/nexus_publish.py               # dry run: resolve and print the plan
    python tools/nexus_publish.py --publish     # actually upload

Nexus API v3. The flow, per the spec:

    POST /uploads                      -> upload id + presigned_url
    PUT  <presigned_url>               -> the bytes
    POST /uploads/{id}/finalise        -> close the session
    GET  /uploads/{id}                 -> poll until state == available
    POST /mod-files/{id}/versions      -> becomes the newest version of the file

Two headers on the PUT are part of the URL signature, so the upload is rejected if
either is missing or does not match: Content-Disposition (the filename sent to
/uploads) and Content-MD5 (base64 of the same digest, not the hex one).

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
MOD_FILE_NAME = "AutoQTE"         # which file on the page to add a version to
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


def archive():
    dist = os.path.join(ROOT, "dist")
    zips = [f for f in os.listdir(dist) if f.startswith("AutoQTE-") and f.endswith(".zip")]
    if len(zips) != 1:
        die("expected exactly one archive in dist/, found %d: %s" % (len(zips), zips))
    return os.path.join(dist, zips[0])


def version_of(path):
    src = open(os.path.join(ROOT, "Scripts", "main.lua"), encoding="utf-8").read()
    m = re.search(r'local VERSION = "([^"]+)"', src)
    if not m:
        die("could not read VERSION from Scripts/main.lua")
    v = m.group(1)
    if v not in os.path.basename(path):
        die("archive %s does not carry version %s - rebuild first" % (os.path.basename(path), v))
    return v


def main():
    publish = "--publish" in sys.argv
    key = os.environ.get("NEXUS_API_KEY", "").strip()
    if not key:
        die("set NEXUS_API_KEY (https://www.nexusmods.com/settings/api-keys)")

    path = archive()
    version = version_of(path)
    blob = open(path, "rb").read()
    digest = hashlib.md5(blob).digest()
    hex_md5 = digest.hex()
    b64_md5 = base64.b64encode(digest).decode()
    filename = os.path.basename(path)

    if not NAME_RE.match(MOD_FILE_NAME) or len(MOD_FILE_NAME) > 50:
        die("mod file name %r fails the API's pattern" % MOD_FILE_NAME)
    if not VERSION_RE.match(version) or len(version) > 50:
        die("version %r fails the API's pattern" % version)

    # Resolve mod -> its files, so the new version lands on the right one.
    mod = call("GET", "/games/%s/mods/%s" % (GAME, MOD), key)["data"]
    files = call("GET", "/mods/%s/files" % mod["id"], key)["data"]["mod_files"]
    match = [f for f in files if f["name"] == MOD_FILE_NAME]
    if len(match) != 1:
        die("expected one mod file named %r, found: %s"
            % (MOD_FILE_NAME, [f["name"] for f in files]))
    mod_file = match[0]

    print("  mod            %s  (%s/%s)" % (mod.get("name") or mod["id"], GAME, MOD))
    print("  mod file       %s  id=%s  versions=%s"
          % (mod_file["name"], mod_file["id"], mod_file.get("versions_count")))
    print("  archive        %s  %d bytes" % (filename, len(blob)))
    print("  version        %s" % version)
    print("  md5            %s" % hex_md5)
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
        "name": MOD_FILE_NAME,
        "version": version,
        "file_category": "main",
        "update_mod_version": True,
        "archive_existing_file": True,
    })["data"]
    print("  version id     %s" % made["version"]["id"])
    print("\n  published %s as %s" % (filename, version))
    print("  https://www.nexusmods.com/%s/mods/%s?tab=files" % (GAME, MOD))


if __name__ == "__main__":
    main()
