#!/usr/bin/env python3
r"""Read-only report on how the mod page looks through the Nexus API.

    python tools/nexus_inspect.py

Reads the key from NEXUS_API_KEY, or from a .nexus-key file beside the repo root
(gitignored). Makes no writes of any kind - only GETs, plus the documented POST
batch lookups, which are reads despite the verb.

v3 gives the name, summary, status, thumbnail, adult flag, the file list with
categories and versions, and the authored requirements. It has no page fields at
all - the live spec at https://api.nexusmods.com/openapi.yaml is 31 endpoints and
none of them return a description, endorsements, downloads or categories.

Legacy v1 still serves those and takes the same apikey header, so the page-fields
section reads from it instead.

Neither exposes the image gallery, tags, permissions or credits. A clean report
here does not mean the page reads well - only that its machine-visible parts are
right.
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

    head("page fields (legacy v1 - not in the v3 spec)")
    # v3 carries no description, endorsements, downloads or categories. v1 still
    # serves them and takes the same apikey header. Printed from what it actually
    # returns rather than from assumed field names.
    v1 = "https://api.nexusmods.com/v1/games/%s/mods/%s.json" % (GAME, MOD)
    req = urllib.request.Request(v1)
    req.add_header("apikey", k)
    req.add_header("Accept", "application/json")
    KNOWN = ("name", "version", "author", "uploaded_by", "summary", "status",
             "available", "category_id", "endorsement_count", "mod_downloads",
             "mod_unique_downloads", "picture_url", "created_time", "updated_time",
             "contains_adult_content", "allow_rating")
    try:
        with urllib.request.urlopen(req) as r:
            d = json.loads(r.read())
        for f in KNOWN:
            if f in d:
                v = d[f]
                if f == "summary" and v:
                    v = str(v)[:70] + ("..." if len(str(v)) > 70 else "")
                print("  %-22s %s" % (f, v if v not in (None, "") else "(empty)"))
        desc = d.get("description") or ""
        print("  %-22s %d chars" % ("description", len(desc)))
        if desc:
            print("  %-22s %s" % ("starts", " ".join(desc.split())[:70] + "..."))
        extra = sorted(set(d) - set(KNOWN) - {"description"})
        if extra:
            print("  %-22s %s" % ("other fields", ", ".join(extra)))
    except urllib.error.HTTPError as e:
        print("  ! v1 mod -> %d  %s" % (e.code, e.read().decode("utf-8", "replace")[:200]))

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

    print("\nStill not visible: the image gallery, tags, permissions and credits.")
    print("v3 has none of the page fields; the section above comes from legacy v1.")


if __name__ == "__main__":
    main()
