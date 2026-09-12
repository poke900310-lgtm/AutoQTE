#!/usr/bin/env python3
r"""Read-only report on how the mod page looks through the Nexus API.

    python tools/nexus_inspect.py

Reads the key from NEXUS_API_KEY, or from a .nexus-key file beside the repo root
(gitignored). Makes no writes of any kind - only GETs, plus the documented POST
batch lookups, which are reads despite the verb.

What the v3 API can show: name, summary, status, thumbnail, adult flag, the file
list with categories and versions, and the authored requirements.

What it cannot: the description body, the image gallery, endorsements, download
counts, categories, tags, permissions or credits. Those are not in the v3 spec,
so a clean report here does not mean the page reads well - only that its
machine-visible parts are right.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.nexusmods.com/v3"
GAME = "thebloodofdawnwalker"
MOD = "456"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def key():
    k = os.environ.get("NEXUS_API_KEY", "").strip()
    if k:
        return k
    path = os.path.join(ROOT, ".nexus-key")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read().strip()
    raise SystemExit(
        "nexus_inspect: no API key.\n"
        "  Either  set NEXUS_API_KEY=...\n"
        "  or      put the key in %s (gitignored)\n"
        "  Get one at https://www.nexusmods.com/settings/api-keys" % path)


def call(method, path, k, body=None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("apikey", k)
    req.add_header("Accept", "application/json")
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        print("  ! %s %s -> %d\n    %s" % (method, path, e.code, detail))
        return None


def head(title):
    print("\n" + title)
    print("-" * len(title))


def main():
    k = key()

    head("mod")
    mod = call("GET", "/games/%s/mods/%s" % (GAME, MOD), k)
    if not mod:
        raise SystemExit("nexus_inspect: could not read the mod; is the key valid?")
    mod = mod["data"]
    print("  id            %s" % mod["id"])
    print("  game_scoped   %s" % mod["game_scoped_id"])
    print("  name          %s" % (mod.get("name") or "(not shown)"))
    print("  url           https://www.nexusmods.com/%s/mods/%s" % (GAME, MOD))

    head("page appearance")
    batch = call("POST", "/mods/batch", k, {"mod_ids": [mod["id"]]})
    rows = (batch or {}).get("data", {}).get("mods", [])
    if not rows:
        print("  (no row returned - the mod may be unpublished or hidden)")
    for m in rows:
        print("  name          %s" % m["name"])
        print("  summary       %s" % (m["summary"] or "(empty)"))
        print("  status        %s" % m["status"])
        print("  adult         %s" % m["adult_content"])
        print("  thumbnail     %s" % (m.get("thumbnail_url") or "(none - no image set)"))

    head("files")
    files = call("GET", "/mods/%s/files" % mod["id"], k)
    for f in (files or {}).get("data", {}).get("mod_files", []):
        print("  %-28s id=%-10s active=%-5s versions=%s archived=%s removed=%s"
              % (f["name"], f["id"], f["is_active"], f["versions_count"],
                 f["archived_count"], f["removed_count"]))
        vers = call("GET", "/mod-files/%s/versions" % f["id"], k)
        for v in (vers or {}).get("data", {}).get("versions", []):
            print("      %-10s %-12s %-14s primary=%-5s %s"
                  % (v["version"], v["category"], v["name"][:14],
                     v.get("is_primary"), v["uploaded_at"]))
            deps = call("GET", "/mod-file-versions/%s/dependencies" % v["id"], k)
            d = (deps or {}).get("dependency_definitions", [])
            dlc = (deps or {}).get("dlc_dependency_definitions", [])
            if d or dlc:
                print("        requirements: %d version-range, %d dlc" % (len(d), len(dlc)))

    head("public feed")
    req = urllib.request.Request(API + "/games/%s/trending-mods" % GAME)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            for m in json.loads(r.read())["data"]["mods"]:
                mark = "<-- yours" if "/%s" % MOD in m["mod_page_url"] else ""
                print("  %-42s %s %s" % (m["name"][:42], m.get("author") or "", mark))
    except urllib.error.HTTPError as e:
        print("  ! trending-mods -> %d" % e.code)

    print("\nNot visible through this API: description body, image gallery,")
    print("endorsements, downloads, categories, tags, permissions, credits.")


if __name__ == "__main__":
    main()
