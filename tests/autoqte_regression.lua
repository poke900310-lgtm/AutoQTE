-- AutoQTE regression suite.
--   usage: lua54.exe autoqte_regression.lua <path to main.lua>
--
-- Contract: every assertion here must be killable. tests/mutants.py breaks one
-- behaviour at a time and each mutant must turn this suite red; a SURVIVED line
-- there means an assertion is not constraining what its name claims.
--
-- The stubs return a truthy phantom for absent UObject members, as UE4SS does.
-- Read members with rawget inside this file, never self.x, or a test can pass
-- by comparing two phantoms.
local target = ...

local VIS_VISIBLE, VIS_COLLAPSED = 0, 1   -- ESlateVisibility
local out, faults = {}, 0
local FAIL_VISIBILITY = false
NOOP_VISIBILITY = false   -- next SetVisibility returns normally and does nothing
PRINT_THROWS = false      -- next print() raises, as a broken logger would
HOOK_FAIL = nil           -- RegisterHook returns nothing for this path
UNREADABLE_VISIBILITY = false   -- Visibility reads back as a phantom, as an enum might
STRING_VISIBILITY = false       -- Visibility reads back as its enumerator NAME
LOG_WRITE_THROWS = false        -- the log file handle raises on write
REFUSE_WIDGET = nil
print = function(s)
    if PRINT_THROWS then PRINT_THROWS = false; error("logger died") end
    out[#out+1] = tostring(s):gsub("\n$","") end
INI = nil   -- per-test AutoQTE.ini contents, or nil for "no file"
INI_THROWS = false
io.open = function(path, mode)
    if mode == "r" then
        if INI and tostring(path):find("AutoQTE.ini", 1, true) then
            local done = false
            return { read = function()
                         if INI_THROWS then error("read blew up") end
                         if done then return nil end done = true; return INI end,
                     close = function() end }
        end
        return nil
    end
    return { write = function() if LOG_WRITE_THROWS then error("write failed") end end,
             flush = function() end, close = function() end }
end

local PHANTOM = setmetatable({}, {__tostring = function() return "<phantom>" end})
local nextAddr = 0x1000

local function mk(spec)
  spec = spec or {}
  nextAddr = nextAddr + 0x10
  local o = { __addr = nextAddr, props = spec.props or {}, cls = spec.cls or "BP_DIS_C",
              name = spec.name or "BP_DIS_C /Game/X", seq = spec.seq,
              vis = spec.vis or 0, completed = 0, freed = false,
              onComplete = spec.onComplete }
  local M = {}
  M.IsValid  = function(self) return not self.freed end
  M.GetAddress = function(self) return self.__addr end
  M.GetFullName = function(self)
      if self.freed then faults = faults + 1; error("ACCESS VIOLATION: GetFullName on freed "..self.name) end
      return self.name end
  M.GetClass = function(self) local c = self.cls
      return { GetFName = function() return { ToString = function() return c end } end } end
  M.GetInteractiveSceneLevelSequence = function(self)
      local q = rawget(self, "seq")
      if q == nil then error("no sequence") end
      return q end
  -- ESlateVisibility: 0 Visible, 1 Collapsed. The mod hides the prompt with the
  -- same property the .pak edition defaults to Collapsed in the asset.
  M.SetVisibility = function(self, v)
      if self.freed then faults = faults + 1; error("ACCESS VIOLATION: SetVisibility on freed") end
      if REFUSE_WIDGET ~= nil and rawequal(self, REFUSE_WIDGET) then
        error("SetVisibility refused by the engine")
    end
    if FAIL_VISIBILITY then FAIL_VISIBILITY = false; error("SetVisibility refused by the engine") end
      if NOOP_VISIBILITY then NOOP_VISIBILITY = false; return end
      self.vis = v end
  if spec.noopComplete then
    -- returns cleanly and does nothing: the shape a renamed or gutted engine
    -- function takes, which a pcall cannot tell apart from success
    M.CompleteCurrentPrompt = function(self) self.completed = self.completed + 1 end
  elseif not spec.noComplete then
    M.CompleteCurrentPrompt = function(self)
        self.completed = self.completed + 1
        self.props.IsPaused = false
        local cb = rawget(self, "onComplete")
        if cb then cb(self) end end
  end
  return setmetatable(o, {__index = function(t, k)
      if M[k] then return M[k] end
      local p = rawget(t, "props")
      if p[k] ~= nil then return p[k] end
      if k == "Visibility" then
        if UNREADABLE_VISIBILITY then return PHANTOM end
        if STRING_VISIBILITY then return ({ [0] = "Visible", "Collapsed", "Hidden" })[rawget(t, "vis")] end
        return rawget(t, "vis") end
      return PHANTOM end})
end

local hooks, binds, keyname = {}, {}, {}
local hid = 0
RegisterHook   = function(path, pre, post)
    if HOOK_FAIL == path then return nil end
    hid = hid + 2; hooks[path] = post; return hid, hid + 1 end
UnregisterHook = function(path) hooks[path] = nil end
RegisterKeyBind = function(k, m, cb) binds[keyname[k] or k] = cb end
IsKeyBindRegistered = function() return false end
ExecuteInGameThread = function(f) f() end
local kc = 100
Key = setmetatable({}, {__index = function(t, k)
    -- F-keys plus the few named keys the README offers; anything else is
    -- "not a key name UE4SS knows", which bind() must handle.
    if type(k) ~= "string" or not (k:match("^F%d+$") or k == "INS" or k == "HOME" or k == "END") then return nil end
    kc = kc + 1; rawset(t, k, kc); keyname[kc] = k; return kc end})
FindAllOf = function() return {} end

local START   = "/Script/DogwoodWorld.InteractiveSceneObject:OnInteractiveScenePlaybackStarted"
local DONE    = "/Script/DogwoodWorld.InteractiveSceneObject:OnCompletedInteractiveSceneNotification"
local CANCEL  = "/Script/DogwoodWorld.InteractiveSceneObject:OnCancelledInteractiveSceneNotification"
local TRIGGER = "/Script/DogwoodWorld.DISLevelSequenceDirector:TriggerDISInteraction"
local SEQNAME = "InteractiveSceneLevelSequence /Game/Q/DialogueInteractions/WoodChopping/LS_DIS_WoodChopping_Long"

local function fresh()
  out, hooks, binds, faults = {}, {}, {}, 0
  FAIL_VISIBILITY = false
  REFUSE_WIDGET = nil
  NOOP_VISIBILITY = false
  PRINT_THROWS = false
  UNREADABLE_VISIBILITY = false
  STRING_VISIBILITY = false
  LOG_WRITE_THROWS = false
  assert(loadfile(target))()
  INI = nil          -- single-use: each test sets it again before fresh()
end
local function logged(pat)
  for _, l in ipairs(out) do if l:find(pat, 1, true) then return l end end end

local function scene(spec)
  spec = spec or {}
  local w = mk{ name = "WBP_DIS_Prompt_New_C /Game/W", vis = 0 }
  local seq = mk{ name = spec.seqName or SEQNAME }
  local a = mk{ name = "BP_DIS_C /Game/M.M:PersistentLevel.BP_DIS_C_UAID_A", seq = seq,
                noComplete = spec.noComplete, noopComplete = spec.noopComplete,
                onComplete = spec.onComplete }

  a.props["Action Prompt"] = w
  if spec.paused == nil then a.props.IsPaused = true else a.props.IsPaused = spec.paused end
  return a, w, seq
end

local pass, fail = 0, 0
local function check(name, ok, detail)
  if ok then pass = pass + 1 else fail = fail + 1 end
  io.write(string.format("  %-5s %s%s\n", ok and "PASS" or "FAIL", name,
                         detail and ("   [" .. tostring(detail) .. "]") or ""))
end

io.write("== V1  REF:219 dangling deref of hiddenWidget (F4 after an untracked teardown)\n")
fresh()
do
  local a, w = scene()
  hooks[START](a)
  check("control: scene skipped and prompt hidden", a.completed == 1 and w.vis == VIS_COLLAPSED,
        "completed=" .. a.completed .. " vis=" .. tostring(w.vis))
  a.freed, w.freed = true, true          -- destroyed with no Completed/Cancelled
  local ok = pcall(function() binds.F4() end)
  check("F4 does not dereference the freed widget", faults == 0, "native faults=" .. faults)
  check("F4 handler itself survives", ok)
end

io.write("== V2  REF:229 a failed restore latches Collapsed as the original visibility\n")
fresh()
do
  local a, w = scene()
  hooks[START](a)
  a.props.IsPaused = true                -- a second prompt in the same scene
  FAIL_VISIBILITY = true                    -- the restore inside hidePrompt fails once
  hooks[TRIGGER]()
  hooks[DONE](a)
  check("prompt is restored to its original visibility", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
end

io.write("== V3  REF:299 CompleteCurrentPrompt refused -> hidden prompt, false 'skipped'\n")
fresh()
do
  local a, w = scene{ noComplete = true }
  hooks[START](a)
  check("does not claim a skip it did not perform", logged("skipped:") == nil, logged("skipped:"))
  check("prompt left visible for the player", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
  check("nothing was completed", a.completed == 0)
end

io.write("== V4  REF:300-304 re-entrant endScene during CompleteCurrentPrompt\n")
fresh()
do
  local a = select(1, scene())
  a.onComplete = function(self) hooks[DONE](self) end   -- game notifies inline
  hooks[START](a)
  local line = logged("skipped:")
  check("skip line keeps the scene identity", line ~= nil and line:find("ls_dis_woodchopping_long", 1, true) ~= nil, line)
end

io.write("== V5  nothing is blocked by default; BlockAlso is what blocks\n")
local PATTERNS = { "vasylflogging", "feedingesme", "forcefeed", "anca_wounds",
                   "patching_marat", "endurance_trial", "breakritual",
                   "eating_mandrake", "takerabbit", "destroying_skates",
                   "filling_grave", "ringingbells", "gettingkey" }
do
  INI = nil; fresh()
  local a = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_vasylflogging_DIS" }
  hooks[START](a)
  check("the shipped list blocks nothing", a.completed == 1, "completed=" .. a.completed)
end
do  -- the cautious reference set documented in AutoQTE.defaults.ini
  local bad = {}
  for _, pat in ipairs(PATTERNS) do
    INI = "BlockAlso = " .. pat .. "\n"; fresh()
    local a = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_" .. pat .. "_DIS" }
    hooks[START](a)
    if a.completed ~= 0 or logged("BLOCKED (" .. pat .. ")") == nil then bad[#bad + 1] = pat end
  end
  check(#PATTERNS .. " reference patterns each block via BlockAlso", #bad == 0,
        #bad > 0 and ("failed: " .. table.concat(bad, ", ")) or nil)
end

io.write("== V6  phantom-userdata defence, each half independently\n")
fresh()
do  -- getScalar's type filter: absent IsPaused yields a truthy phantom
  local a = scene{ paused = false }
  a.props.IsPaused = nil
  hooks[START](a)
  check("absent IsPaused is not treated as pending", a.completed == 0, "completed=" .. a.completed)
end
fresh()
do  -- the `== true` test: a truthy non-boolean must not pass either
  local a = scene{ paused = "true" }
  hooks[START](a)
  check("string true is not treated as pending", a.completed == 0, "completed=" .. a.completed)
end
fresh()
do
  local a = scene{ paused = 1 }
  hooks[START](a)
  check("number 1 is not treated as pending", a.completed == 0, "completed=" .. a.completed)
end

io.write("== V7  a dead actor is never driven\n")
fresh()
do
  local a = scene()
  hooks[START](a)
  local before = a.completed
  a.freed = true
  hooks[TRIGGER]()
  check("trigger on a freed actor completes nothing more", a.completed == before,
        "completed=" .. a.completed)
  check("the scene is disowned", logged("actor invalid") ~= nil)
end

io.write("== V8  the prompt widget is never left hidden\n")
fresh()
do  -- the game swaps the prompt widget mid-scene: the old one must be restored
  local a, w1 = scene()
  hooks[START](a)
  local w2 = mk{ name = "WBP_DIS_Prompt_New_C /Game/W2", vis = 0 }
  a.props["Action Prompt"] = w2
  a.props.IsPaused = true
  hooks[TRIGGER]()
  hooks[DONE](a)
  check("first widget restored, not stranded", w1.vis == VIS_VISIBLE, "w1=" .. tostring(w1.vis))
  check("second widget restored", w2.vis == VIS_VISIBLE, "w2=" .. tostring(w2.vis))
end
fresh()
do  -- slot reuse: alive, same full name, still Collapsed by us, different object.
    -- Only the address check can tell it apart, so this isolates that check.
  local a, w = scene()
  hooks[START](a)
  w.__addr = 0x900000      -- the proxy now resolves to something else
  hooks[DONE](a)
  check("a same-named object at a new address is not restored", w.vis == VIS_COLLAPSED,
        "vis=" .. tostring(w.vis))
end

io.write("== V10  F4 toggles in both directions, mid-scene\n")
fresh()
do  -- disabled BEFORE the scene starts, re-enabled partway through
  binds.F4()                          -- off
  local a = scene()
  hooks[START](a)
  check("nothing completed while disabled", a.completed == 0, "completed=" .. a.completed)
  binds.F4()                          -- on, mid-scene
  a.props.IsPaused = true
  hooks[TRIGGER]()
  check("re-enabling mid-scene resumes", a.completed == 1, "completed=" .. a.completed)
end
fresh()
do  -- enabled at start, disabled partway, re-enabled again
  local a, w = scene()
  hooks[START](a)
  local n = a.completed
  binds.F4()                          -- off, mid-scene
  check("prompt restored when disabled mid-scene", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
  a.props.IsPaused = true
  hooks[TRIGGER]()
  check("nothing completed while disabled", a.completed == n, "completed=" .. a.completed)
  binds.F4()                          -- on again
  a.props.IsPaused = true
  hooks[TRIGGER]()
  check("re-enabling resumes again", a.completed == n + 1, "completed=" .. a.completed)
end

io.write("== V11  co-existence: never clobber another mod's write to the prompt widget\n")
fresh()
do  -- another HUD mod fades the same widget while AutoQTE has it hidden
  local a, w = scene()
  hooks[START](a)
  check("AutoQTE hid the prompt", w.vis == VIS_COLLAPSED, "vis=" .. tostring(w.vis))
  w.vis = 3                       -- another mod mid-fade, after our write
  hooks[DONE](a)
  check("the other mod's value survives", w.vis == 3, "vis=" .. tostring(w.vis))
end
fresh()
do  -- unchanged since our write: we must still restore it
  local a, w = scene()
  hooks[START](a)
  hooks[DONE](a)
  check("our own write is still undone", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
end
fresh()
do  -- the widget was already faded by someone else before we hid it
  local a, w = scene{}
  w.vis = 3
  hooks[START](a)
  hooks[DONE](a)
  check("a pre-existing value is put back, not Visible", w.vis == 3, "vis=" .. tostring(w.vis))
end

io.write("== V12  AutoQTE.ini\n")
do  -- no ini at all: built-in defaults stand
  INI = nil; fresh()
  local a, w = scene()
  hooks[START](a)
  check("no ini -> defaults still work", a.completed == 1 and w.vis == VIS_COLLAPSED,
        "completed=" .. a.completed .. " vis=" .. tostring(w.vis))
end
do  -- Enabled = false
  INI = "Enabled = false\n"; fresh()
  local a = scene()
  hooks[START](a)
  check("Enabled=false is honoured", a.completed == 0, "completed=" .. a.completed)
end
do  -- HidePrompt = false
  INI = "HidePrompt = no\n"; fresh()
  local a, w = scene()
  hooks[START](a)
  check("HidePrompt=no is honoured", a.completed == 1 and w.vis == VIS_VISIBLE,
        "vis=" .. tostring(w.vis))
end
do  -- BlockAlso adds patterns
  INI = "; a comment\n[Section]\nBlockAlso = woodchopping , SomeOtherScene\n"; fresh()
  local a = scene()
  hooks[START](a)
  check("BlockAlso blocks a scene the shipped list allows", a.completed == 0,
        "completed=" .. a.completed)
  check("and says which pattern matched", logged("BLOCKED (woodchopping)") ~= nil)
end
do  -- keys come from the ini
  INI = "ToggleKey = F7\nDiagnoseKey =\n"; fresh()
  check("ToggleKey=F7 binds F7", binds.F7 ~= nil)
  check("and not the default F4", binds.F4 == nil)
  check("an empty DiagnoseKey binds nothing", binds.INS == nil)
end
do  -- junk must not break anything
  INI = "!!! garbage\n= = =\nEnabled\nNoSuchSetting = 12\nEnabled = true\n\n\n"; fresh()
  local a = scene()
  hooks[START](a)
  check("a malformed ini still loads and works", a.completed == 1, "completed=" .. a.completed)
  check("and reports the lines it could not read", logged("not understood") ~= nil)
end
do  -- empty and junk BlockAlso entries must not disturb a real one
  INI = "BlockAlso =\nBlockAlso = ,,,\nBlockAlso = takerabbit\n"; fresh()
  local a = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_takerabbit_DIS" }
  hooks[START](a)
  check("a real BlockAlso survives empty ones beside it", a.completed == 0,
        "completed=" .. a.completed)
end

io.write("== V13  the ini accepts what the docs taught, and never drops a line in silence\n")
do  -- v1.0.0's README documented DIS.HidePrompt; it must not be silently discarded
  INI = "DIS.HidePrompt = false\n"; fresh()
  local a, w = scene()
  hooks[START](a)
  check("a dotted key is honoured", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
end
do  -- v1.0.0's README documented quoted key names
  INI = 'ToggleKey = "F7"\n'; fresh()
  check("a quoted value is unquoted", binds.F7 ~= nil)
end
do  -- an inline comment must not become part of the value
  INI = "ToggleKey = F7 ; my key\n"; fresh()
  check("an inline comment is stripped", binds.F7 ~= nil)
end
do  -- the README's quoted BlockAlso form must actually block, not just count
  INI = 'BlockAlso = "takerabbit", "woodchopping"\n'; fresh()
  local a = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_takerabbit_DIS" }
  hooks[START](a)
  check("a quoted BlockAlso item blocks rather than fails open", a.completed == 0,
        "completed=" .. a.completed)
end
do  -- a bare ; or # is part of the value: truncating it BROADENS the pattern
  INI = "BlockAlso = takerabbit#stew\n"; fresh()
  local a = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_takerabbit_DIS" }
  hooks[START](a)
  check("a # inside a value does not truncate it into a broader pattern",
        a.completed == 1, "completed=" .. a.completed)
end
do  -- ...while a real inline comment after whitespace is still removed
  INI = "BlockAlso = takerabbit ; my note\n"; fresh()
  local a = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_takerabbit_DIS" }
  hooks[START](a)
  check("an inline comment after whitespace is still stripped from BlockAlso",
        a.completed == 0, "completed=" .. a.completed)
end
do  -- a completion that returns but does nothing must not be reported as a skip
  INI = nil; fresh()
  local a, w = scene{ noopComplete = true }
  hooks[START](a)
  check("a no-op completion is not announced as skipped", logged("skipped:") == nil)
  check("and it says the prompt is still pending",
        logged("still pending") ~= nil)
  check("and the prompt is handed back, not left Collapsed",
        w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
end
do  -- an unrecognised scene still supersedes the one being tracked
  INI = nil; fresh()
  local a = scene()
  hooks[START](a)                                   -- track a real DIS scene
  local other = mk{ name = "BP_Other_C /Game/O", cls = "BP_Other_C" }
  hooks[START](other)                               -- unexpected class arrives
  check("an unexpected class is reported",
        logged("unexpected class") ~= nil)
  check("and it supersedes the tracked scene", logged("superseded") ~= nil)
  local before = a.completed
  hooks[TRIGGER](a)
  check("so a later trigger cannot complete the finished scene",
        a.completed == before, "completed " .. before .. " -> " .. a.completed)
end
do  -- a widget we still owe a restore to must not be forgotten for a new one
  INI = nil; fresh()
  local a1, w1 = scene()
  hooks[START](a1)
  check("first widget hidden", w1.vis == VIS_COLLAPSED, "vis=" .. tostring(w1.vis))
  -- Only w1 refuses writes, so its restore fails while the next widget hides
  -- fine. That is the shape that strands it.
  REFUSE_WIDGET = w1
  local a2, w2 = scene()
  hooks[START](a2)
  check("a second widget is not hidden while w1 is still owed a restore",
        w2.vis == VIS_VISIBLE, "w2=" .. tostring(w2.vis))
  REFUSE_WIDGET = nil
  local a3 = scene()
  hooks[START](a3)
  check("and w1 is recovered once writes work again",
        w1.vis == VIS_VISIBLE, "w1=" .. tostring(w1.vis))
end
do  -- a parser fault must be reported, not swallowed
  -- fresh() deliberately does not reset this, so the throw survives into the
  -- load it is meant to break; the test clears it again straight after.
  INI = "Enabled = false"; INI_THROWS = true; fresh(); INI_THROWS = false
  check("an ini read that throws is logged", logged("could not be read") ~= nil)
end
do  -- FindAllOf is only needed by the diagnose sweep, not by the mod
  INI = nil
  local saved = FindAllOf
  FindAllOf = nil
  fresh()
  FindAllOf = saved
  check("a build without FindAllOf still hooks and runs",
        logged("AutoQTE disabled") == nil and hooks[START] ~= nil)
end
do  -- a line that parses as nothing must still be reported
  INI = "BlockAlso = one,\n            two, three\n"; fresh()
  check("a continuation line is reported, not dropped", logged("not understood") ~= nil)
end
do  -- a UTF-8 BOM must not eat the first setting
  INI = "\239\187\191Enabled = false\n"; fresh()
  local a = scene()
  hooks[START](a)
  check("a BOM does not eat the first setting", a.completed == 0, "completed=" .. a.completed)
end
do  -- with no ini at all the mod must say so rather than stay silent
  INI = nil; fresh()
  check("a missing ini is announced", logged("using built-in defaults") ~= nil)
end

io.write("== V14  a refused restore must not hide the prompt for the rest of the session\n")
do
  INI = nil; fresh()
  local w = mk{ name = "WBP_DIS_Prompt_New_C /Game/W", vis = 0 }
  local function sc(tag)
    local s = mk{ name = "InteractiveSceneLevelSequence /Game/Q/DIS/ls_" .. tag }
    local a = mk{ name = "BP_DIS_C /Game/M.M:PersistentLevel.BP_DIS_C_UAID_" .. tag, seq = s }
    a.props.IsPaused = true; a.props["Action Prompt"] = w
    return a
  end
  local a1 = sc("one"); hooks[START](a1)
  FAIL_VISIBILITY = true                      -- the restore at scene end is refused
  hooks[DONE](a1)
  check("the prompt is left hidden by the refusal", w.vis == VIS_COLLAPSED, "vis=" .. tostring(w.vis))
  local a2 = sc("two"); hooks[START](a2); hooks[DONE](a2)
  check("the next scene recovers it", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
end

io.write("== V15  the cancel hook releases the scene and restores the prompt\n")
do
  INI = nil; fresh()
  local a, w = scene()
  hooks[START](a)
  check("prompt hidden while the scene runs", w.vis == VIS_COLLAPSED, "vis=" .. tostring(w.vis))
  hooks[CANCEL](a)
  check("cancel restores the prompt", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
  check("cancel releases the scene", logged("scene ended (cancelled)") ~= nil)
end

io.write("== V16  the diagnose key reports the identity the blocklist matches on\n")
do
  INI = nil; fresh()
  local a = scene()
  hooks[START](a)
  binds.INS()
  check("a property the actor does not have is not listed", logged("PauseElapsedTime") == nil)
  check("diagnose prints the scene identity", logged("scene: ") ~= nil)
  check("and it is the level-sequence half, not just the actor",
        logged("ls_dis_woodchopping_long") ~= nil)
end


io.write("== V17  a SetVisibility that returns but does nothing is not trusted\n")
fresh()
do  -- the restore at scene end silently fails: the widget must stay owed, not be forgotten
  local a, w = scene()
  hooks[START](a)
  NOOP_VISIBILITY = true
  hooks[DONE](a)
  check("a no-op restore leaves the widget Collapsed", w.vis == VIS_COLLAPSED, "vis=" .. tostring(w.vis))
  local b, w2 = scene()
  hooks[START](b)
  check("the owed widget is restored at the next opportunity", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
  check("and the new prompt is hidden", w2.vis == VIS_COLLAPSED, "vis=" .. tostring(w2.vis))
end

io.write("== V18  F4 must not claim ENABLED when the hooks never registered\n")
HOOK_FAIL = TRIGGER
fresh()
HOOK_FAIL = nil
do
  check("a missing hook disables the DIS hooks", logged("AutoQTE disabled") ~= nil)
  binds.F4()
  binds.F4()
  check("F4 never reports ENABLED", logged(">>> AutoQTE ENABLED") == nil)
  check("and says why", logged("cannot be enabled") ~= nil)
end

io.write("== V19  an error inside a hook callback is contained; the scene is kept and the mod stays on\n")
fresh()
do
  local a = scene()
  PRINT_THROWS = true                     -- the first log line inside the hook blows up
  local ok = pcall(hooks[START], a)
  check("the error does not escape the hook", ok)
  check("it is reported", logged("hook raised an error") ~= nil)
  a.props.IsPaused = true
  hooks[TRIGGER]()
  check("the scene is kept, not abandoned: the next trigger completes it", a.completed == 1, "completed=" .. a.completed)
  local b = scene()
  hooks[START](b)
  check("automation continues for the next scene", b.completed == 1, "completed=" .. b.completed)
end

io.write("== V20  an unreadable scene-start context releases the tracked scene\n")
fresh()
do
  local a, w = scene()
  hooks[START](a)
  check("control: prompt hidden", w.vis == VIS_COLLAPSED, "vis=" .. tostring(w.vis))
  hooks[START](nil)
  check("the tracked scene is released", logged("scene-start context unreadable") ~= nil)
  check("and its prompt restored", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
  a.props.IsPaused = true
  hooks[TRIGGER]()
  check("the released scene is not driven again", a.completed == 1, "completed=" .. a.completed)
end


io.write("== V21  an unreadable Visibility read-back is not treated as a failed write\n")
fresh()
do
  local a, w = scene()
  UNREADABLE_VISIBILITY = true
  hooks[START](a)
  check("control: the engine applied the hide", w.vis == VIS_COLLAPSED, "vis=" .. tostring(w.vis))
  hooks[DONE](a)
  check("the widget was latched and is restored at scene end", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
end


io.write("== V22  a Visibility that reads back as an enumerator NAME is not a failed write\n")
fresh()
do
  local a, w = scene()
  STRING_VISIBILITY = true
  hooks[START](a)
  check("control: the engine applied the hide", w.vis == VIS_COLLAPSED, "vis=" .. tostring(w.vis))
  hooks[DONE](a)
  check("the widget was latched and is restored at scene end", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
end

io.write("== V23  a second playback start for the same actor is not a second scene\n")
fresh()
do
  local a, w = scene()
  hooks[START](a)
  a.props.IsPaused = true
  hooks[START](a)
  local n = 0
  for _, l in ipairs(out) do if l:find("skipped:", 1, true) then n = n + 1 end end
  check("skipped: is announced once", n == 1, "skipped lines=" .. n)
  check("the pending prompt is still completed", a.completed == 2, "completed=" .. a.completed)
  check("and the prompt stays hidden", w.vis == VIS_COLLAPSED, "vis=" .. tostring(w.vis))
end

io.write("== V24  a same-address object with a DIFFERENT name is not restored\n")
fresh()
do
  local a, w = scene()
  hooks[START](a)
  w.name = "WBP_DIS_Prompt_New_C /Game/W_replacement"   -- same address, new identity
  hooks[DONE](a)
  check("the replacement is left alone", w.vis == VIS_COLLAPSED, "vis=" .. tostring(w.vis))
end

io.write("== V25  a bare trailing separator does not spoil a value\n")
INI = "Enabled = false;" .. "\n"
fresh()
do
  local a = scene()
  hooks[START](a)
  check("Enabled = false; is read as false", a.completed == 0, "completed=" .. a.completed)
end

io.write("== V26  a log handle that cannot be written never aborts the caller\n")
INI = "Verbose = true" .. "\n"
fresh()
LOG_WRITE_THROWS = true      -- after fresh(), which resets it: the load must succeed first
do
  local a, w = scene{ noComplete = true }
  local ok = pcall(hooks[START], a)
  check("the hook survives", ok)
  check("the refusal still hands the scene back", logged("scene ended (completion refused)") ~= nil)
  check("and the prompt is restored", w.vis == VIS_VISIBLE, "vis=" .. tostring(w.vis))
end
LOG_WRITE_THROWS = false

io.write(string.format("\n%d passed, %d failed\n", pass, fail))
os.exit(fail == 0 and 0 or 1)
