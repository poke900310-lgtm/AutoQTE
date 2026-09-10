#!/usr/bin/env python3
"""Mutation-test the regression suite.

    python tests/mutants.py <path to lua54.exe>

Every assertion in tests/autoqte_regression.lua should be killable: break the
behaviour it covers and the suite must go red. A SURVIVED line means the suite
cannot see that bug, which is the failure mode this project keeps hitting --
a green suite that proves nothing.

Known survivor: getScalar's type filter has no independently observable effect,
because every consumer guards the value again (`== true`, `type(was) ==
"number"`). It is defence-in-depth, not dead code, and is deliberately absent
from the table below.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Scripts", "main.lua")
SUITE = os.path.join(ROOT, "tests", "autoqte_regression.lua")
OUT = os.path.join(ROOT, "tests", "mut")

MUTANTS = [
    ("blocklist_never_matches",
     'if id:find(pat, 1, true) then return pat end', 'if false then return pat end'),
    ("paused_test_weakened",
     'return getScalar(actor, P_PAUSED) == true', 'return getScalar(actor, P_PAUSED) ~= nil'),
    ("isAlive_always_true",
     'local ok, v = pcall(function() return obj:IsValid() end)\n    return ok and v',
     'local ok, v = pcall(function() return obj:IsValid() end)\n    return true'),
    ("restore_is_a_noop",
     'restored = setOpacity(hiddenWidget, hiddenOpacity or 1.0)', 'restored = true'),
    ("restore_addr_check_gone",
     'and addressOf(hiddenWidget) == hiddenAddr and fullName(hiddenWidget) == hiddenName',
     'and fullName(hiddenWidget) == hiddenName'),
    ("restore_isAlive_gone",
     'if hiddenWidget and isAlive(hiddenWidget)\n       and addressOf',
     'if hiddenWidget and (true)\n       and addressOf'),
    ("latch_guard_gone",
     'if not restored and was == 0.0 then was = prev end',
     'if false then was = prev end'),
    ("restore_latch_dropped_on_refusal",
     '    if restored then\n        hiddenWidget, hiddenName, hiddenAddr, hiddenOpacity = nil, nil, nil, nil\n    end',
     '    hiddenWidget, hiddenName, hiddenAddr, hiddenOpacity = nil, nil, nil, nil'),
    ("ini_line_dropped_silently",
     'elseif line:match("%S") then',
     'elseif false then'),
    ("ini_dotted_key_rejected",
     '("^%s*([%w_.]+)%s*=%s*(.-)%s*$")',
     '("^%s*([%w_]+)%s*=%s*(.-)%s*$")'),
    ("ini_quotes_not_stripped",
     """v = v:match('^"(.*)"$') or v:match("^'(.*)'$") or v""",
     'v = v'),
    ("ini_bom_not_stripped",
     'body = body:gsub("^\\239\\187\\191", "")',
     'body = body'),
    ("diagnose_omits_scene",
     'log("scene: %s", sceneIdentity(actor) or "<unidentified>")',
     'local _ = actor'),
    ("cancel_hook_inert",
     'if sameActor(a, scene) then endScene("cancelled") end',
     'local _ = a'),
    ("complete_result_ignored",
     'if not (call(actor, "CompleteCurrentPrompt")) then',
     'if false then call(actor, "CompleteCurrentPrompt") ; end if false then'),
    ("clobbers_other_mods",
     '       and getScalar(hiddenWidget, "RenderOpacity") == 0.0 then',
     '       and true then'),
    ("ini_never_read",
     'pcall(applyIni)', 'local _ = applyIni'),
    ("ini_blockalso_ignored",
     'Config.BlockedScenes[#Config.BlockedScenes + 1] = pat', 'local _ = pat'),
    ("ini_bools_broken",
     'if v == "false" or v == "0" or v == "no"  or v == "off" then return false end',
     'if false then return false end'),
    ("toggle_gates_watching",
     '    if not Config.DIS.Enabled then return end',
     '    if not Config.Enabled or not Config.DIS.Enabled then return end'),
]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__.strip().splitlines()[2].strip())
    lua = sys.argv[1]
    base = open(SRC, encoding="utf-8", newline="").read()
    os.makedirs(OUT, exist_ok=True)
    for stale in os.listdir(OUT):                 # a renamed entry must not leave dead files
        if stale.endswith(".lua") and stale[:-4] not in {m[0] for m in MUTANTS}:
            os.remove(os.path.join(OUT, stale))

    if subprocess.call([lua, SUITE, SRC], stdout=subprocess.DEVNULL) != 0:
        sys.exit("the suite does not pass on unmutated source; fix that first")

    survivors = []
    for name, old, new in MUTANTS:
        found = base.count(old)
        if found != 1:
            sys.exit("mutant %s matches %d times; update tests/mutants.py" % (name, found))
        path = os.path.join(OUT, name + ".lua")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(base.replace(old, new))
        killed = subprocess.call([lua, SUITE, path], stdout=subprocess.DEVNULL) != 0
        print("  %-8s %s" % ("killed" if killed else "SURVIVED", name))
        if not killed:
            survivors.append(name)

    print("\n%d survivors of %d" % (len(survivors), len(MUTANTS)))
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
