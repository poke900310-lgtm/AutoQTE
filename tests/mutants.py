#!/usr/bin/env python3
"""Mutation-test the regression suite.

    python tests/mutants.py <path to lua54.exe>

Every assertion in tests/autoqte_regression.lua should be killable: break the
behaviour it covers and the suite must go red. A SURVIVED line means the suite
cannot see that bug, which is the failure mode this project keeps hitting --
a green suite that proves nothing.

Also deliberately untested: the pcall around applyIni itself. Every fault it
could catch is already caught closer to its source (iniBody pcalls the open, the
read and the close), so there is no input that reaches it -- it is a backstop,
not a code path, and no mutant targets it.

getScalar's type filter used to be an unobservable defence-in-depth (every
consumer re-guarded the value). Since 1.0.8 setVisibility's read-back consumes
it directly; and the diagnose key prints only members the actor really has.
It is observable and in the table (killed by V16's diagnose assertion).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Scripts", "main.lua")
SUITE = os.path.join(ROOT, "tests", "autoqte_regression.lua")
OUT = os.path.join(ROOT, "tests", "mut")

MUTANTS = [
    ("completion_return_taken_as_success",
     'if promptPending(actor) then',
     'if false then'),
    ("unknown_class_leaves_scene_tracked",
     'if not (sceneAddr and ad == sceneAddr and nm == sceneName) then endScene("superseded", actor) end'
     + chr(10) + '    local cls = classOf(actor)',
     'local cls = classOf(actor)'),
    ("hide_forgets_an_owed_restore",
     'if not restored and not (hiddenAddr and ad == hiddenAddr and nm == hiddenName) then',
     'if false then'),
    ("unreadable_ini_reported_as_absent",
     'log("%s opened but could not be read: %s", name, tostring(body))',
     'local _ = body'),
    ("blockalso_reads_the_unquoted_value",
     'for pat in raw:gmatch("[^,]+") do', 'for pat in v:gmatch("[^,]+") do'),
    ("comment_strip_truncates_a_bare_hash",
     'v = v:gsub("%s+[;#].*$", ""):gsub("[;#]+$", "")',
     'v = v:gsub("%s*[;#].*$", "")'),
    ("blocklist_never_matches",
     'if id:find(pat, 1, true) then return pat end', 'if false then return pat end'),
    ("paused_test_weakened",
     'return getScalar(actor, P_PAUSED) == true', 'return getScalar(actor, P_PAUSED) ~= nil'),
    ("isAlive_always_true",
     'local ok, v = pcall(function() return obj:IsValid() end)\n    return ok and v',
     'local ok, v = pcall(function() return obj:IsValid() end)\n    return true'),
    ("restore_is_a_noop",
     'restored = setVisibility(w, hiddenVis or VIS_VISIBLE)', 'restored = true'),
    ("restore_addr_check_gone",
     'if w and addressOf(w) == hiddenAddr and fullName(w) == hiddenName then',
     'if w and fullName(w) == hiddenName then'),
    ("latch_guard_gone",
     'if not restored and was == VIS_COLLAPSED then was = prev end',
     'if false then was = prev end'),
    ("restore_latch_dropped_on_refusal",
     '    if restored then\n        hiddenName, hiddenAddr, hiddenVis, hiddenClass = nil, nil, nil, nil\n    end',
     '    hiddenName, hiddenAddr, hiddenVis, hiddenClass = nil, nil, nil, nil'),
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
     'endScene("cancelled", a)',
     'local _ = a'),
    ("complete_result_ignored",
     'if not (call(actor, "CompleteCurrentPrompt")) then',
     'if false then call(actor, "CompleteCurrentPrompt") ; end if false then'),
    ("ini_never_read",
     'local ok, err = pcall(applyIni)',
     'local ok, err = true, nil'),
    ("ini_blockalso_ignored",
     'Config.BlockedScenes[#Config.BlockedScenes + 1] = pat', 'local _ = pat'),
    ("ini_bools_broken",
     'if v == "false" or v == "0" or v == "no"  or v == "off" then return false end',
     'if false then return false end'),
    ("toggle_gates_watching",
     '    if not Config.DIS.Enabled then return end',
     '    if not Config.Enabled or not Config.DIS.Enabled then return end'),
    # 1.0.8 hardening - each mutant reverts one item; V17-V20 must go red
    ("visibility_readback_gone",
     "    return type(back) ~= \"number\" or back == value",
     "    return true"),
    ("unreadable_readback_distrusted",
     "    return type(back) ~= \"number\" or back == value",
     "    return back == value"),
    ("clobbers_other_mods",
     "        if type(cur) ~= \"number\" or cur == VIS_COLLAPSED then",
     "        if true then"),
    ("f4_hook_guard_gone",
     "        if not Config.DIS.Enabled then" + chr(10) + "            log(" + chr(34) + "AutoQTE cannot be enabled - the DIS hooks are unavailable" + chr(34) + ")" + chr(10) + "            return" + chr(10) + "        end" + chr(10),
     ""),
    ("hook_callback_unguarded",
     "        local okc, err = xpcall(cb, debug.traceback, ...)",
     "        local okc, err = true, cb(...)"),
    ("start_context_release_gone",
     "        elseif sceneAddr then",
     "        elseif false then"),
    # review fixes after 1.0.8 hardening
    ('getscalar_filter_gone',
     '    if t == "boolean" or t == "number" or t == "string" then return v end\n    return nil',
     '    return v'),
    ('restore_name_check_gone',
     'if w and addressOf(w) == hiddenAddr and fullName(w) == hiddenName then',
     'if w and addressOf(w) == hiddenAddr then'),
    ('trailing_separator_strip_gone',
     'v = v:gsub("%s+[;#].*$", ""):gsub("[;#]+$", "")',
     'v = v:gsub("%s+[;#].*$", "")'),
    ('log_write_unguarded',
     '        if logFile and not pcall(function() logFile:write(msg .. "\\n"); logFile:flush() end) then\n            logFile = false\n        end',
     '        if logFile then logFile:write(msg .. "\\n"); logFile:flush() end'),
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
