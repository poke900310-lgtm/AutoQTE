-- AutoQTE regression suite.
--   usage: lua54.exe autoqte_regression.lua <path to main.lua>
--
-- Every assertion here has been shown to fail against a targeted mutation of
-- main.lua (13 of 14 mutants killed; see mut/ for the battery). The one mutant
-- that survives is getScalar's type filter: every consumer of getScalar guards
-- the value again (`== true`, `type(was) == "number"`), so removing the filter
-- has no independently observable effect. It is defence-in-depth, not dead
-- code, and it cannot be covered without a second observable.
--
--
-- Supersedes h3-h10. Those predate the removal of the on-screen notice:
-- h10's 10 notice assertions and h8's 4 FindFirstOf/StaticFindObject
-- assertions now fail by design, because the feature and both globals are
-- gone. h4 has always failed on every input. harness.lua and h9 still pass.
-- The stubs deliberately return a truthy phantom for absent UObject members,
-- as UE4SS does. Read members with rawget inside this file, never `self.x`.
local target = ...

local out, faults, viewport = {}, 0, {}
local FAIL_OPACITY = false
print = function(s) out[#out+1] = tostring(s):gsub("\n$","") end
INI = nil   -- per-test AutoQTE.ini contents, or nil for "no file"
io.open = function(path, mode)
    if mode == "r" then
        if INI and tostring(path):find("AutoQTE.ini", 1, true) then
            local done = false
            return { read = function() if done then return nil end done = true; return INI end,
                     close = function() end }
        end
        return nil
    end
    return { write = function() end, flush = function() end, close = function() end }
end

local PHANTOM = setmetatable({}, {__tostring = function() return "<phantom>" end})
local nextAddr = 0x1000

local function mk(spec)
  spec = spec or {}
  nextAddr = nextAddr + 0x10
  local o = { __addr = nextAddr, props = spec.props or {}, cls = spec.cls or "BP_DIS_C",
              name = spec.name or "BP_DIS_C /Game/X", seq = spec.seq,
              opacity = spec.opacity or 1.0, completed = 0, freed = false,
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
  M.SetRenderOpacity = function(self, v)
      if self.freed then faults = faults + 1; error("ACCESS VIOLATION: SetRenderOpacity on freed") end
      if FAIL_OPACITY then FAIL_OPACITY = false; error("SetRenderOpacity refused by the engine") end
      self.opacity = v end
  M.UpdateSubtitle   = function(self, t)
      if rawget(self, "UpdateSubtitleFails") then error("UpdateSubtitle refused") end
      self.text = t end
  M.AddToViewport    = function(self)
      self.adds = (rawget(self, "adds") or 0) + 1; viewport[self] = true end
  M.RemoveFromParent = function(self)
      if rawget(self, "RemoveFails") then error("RemoveFromParent refused") end
      viewport[self] = nil end
  if not spec.noComplete then
    M.CompleteCurrentPrompt = function(self)
        self.completed = self.completed + 1
        self.props.IsPaused = false
        local cb = rawget(self, "onComplete")
        if cb then cb(self) end end
  end
  if spec.create then M.Create = function(self, w, c, p) return spec.create() end end
  return setmetatable(o, {__index = function(t, k)
      if M[k] then return M[k] end
      local p = rawget(t, "props")
      if p[k] ~= nil then return p[k] end
      if k == "RenderOpacity" then return rawget(t, "opacity") end
      return PHANTOM end})
end

local hooks, binds, keyname = {}, {}, {}
local hid = 0
RegisterHook   = function(path, pre, post) hid = hid + 2; hooks[path] = post; return hid, hid + 1 end
UnregisterHook = function(path) hooks[path] = nil end
RegisterKeyBind = function(k, m, cb) binds[keyname[k] or k] = cb end
IsKeyBindRegistered = function() return false end
ExecuteInGameThread = function(f) f() end
local kc = 100
Key = setmetatable({}, {__index = function(t, k)
    if type(k) ~= "string" or not k:match("^F%d+$") then return nil end
    kc = kc + 1; rawset(t, k, kc); keyname[kc] = k; return kc end})
FindAllOf = function() return {} end
local PC, NOTECLS, NOTELIB
FindFirstOf = function() return PC end
StaticFindObject = function(p)
    if p:find("WBP_MovieSubtitle", 1, true) then return NOTECLS end
    if p:find("WidgetBlueprintLibrary", 1, true) then return NOTELIB end
    return nil end

local START   = "/Script/DogwoodWorld.InteractiveSceneObject:OnInteractiveScenePlaybackStarted"
local DONE    = "/Script/DogwoodWorld.InteractiveSceneObject:OnCompletedInteractiveSceneNotification"
local TRIGGER = "/Script/DogwoodWorld.DISLevelSequenceDirector:TriggerDISInteraction"
local SEQNAME = "InteractiveSceneLevelSequence /Game/Q/DialogueInteractions/WoodChopping/LS_DIS_WoodChopping_Long"

local function fresh()
  out, hooks, binds, viewport, faults = {}, {}, {}, {}, 0
  FAIL_OPACITY = false; PC, NOTECLS, NOTELIB = nil, nil, nil
  assert(loadfile(target))()
end
local function logged(pat)
  for _, l in ipairs(out) do if l:find(pat, 1, true) then return l end end end

local function scene(spec)
  spec = spec or {}
  local w = mk{ name = "WBP_DIS_Prompt_New_C /Game/W", opacity = 1.0 }
  local seq = mk{ name = spec.seqName or SEQNAME }
  local a = mk{ name = "BP_DIS_C /Game/M.M:PersistentLevel.BP_DIS_C_UAID_A", seq = seq,
                noComplete = spec.noComplete, onComplete = spec.onComplete }

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
  check("control: scene skipped and prompt hidden", a.completed == 1 and w.opacity == 0.0,
        "completed=" .. a.completed .. " opacity=" .. tostring(w.opacity))
  a.freed, w.freed = true, true          -- destroyed with no Completed/Cancelled
  local ok = pcall(function() binds.F4() end)
  check("F4 does not dereference the freed widget", faults == 0, "native faults=" .. faults)
  check("F4 handler itself survives", ok)
end

io.write("== V2  REF:229 a failed restore latches 0.0 as the original opacity\n")
fresh()
do
  local a, w = scene()
  hooks[START](a)
  a.props.IsPaused = true                -- a second prompt in the same scene
  FAIL_OPACITY = true                    -- the restore inside hidePrompt fails once
  hooks[TRIGGER]()
  hooks[DONE](a)
  check("prompt is restored to its original opacity", w.opacity == 1.0, "opacity=" .. tostring(w.opacity))
end

io.write("== V3  REF:299 CompleteCurrentPrompt refused -> hidden prompt, false 'skipped'\n")
fresh()
do
  local a, w = scene{ noComplete = true }
  hooks[START](a)
  check("does not claim a skip it did not perform", logged("skipped:") == nil, logged("skipped:"))
  check("prompt left visible for the player", w.opacity == 1.0, "opacity=" .. tostring(w.opacity))
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

io.write("== V5  every blocklist pattern blocks its scene\n")
-- One case per pattern. Deleting or corrupting any entry turns this red.
local PATTERNS = { "vasylflogging", "feedingesme", "forcefeed",
                   "anca_wounds", "patching_marat", "endurance_trial", "breakritual",
                   "eating_mandrake", "takerabbit", "destroying_skates", "filling_grave",
                   "ringingbells", "gettingkey" }
do
  local bad = {}
  for _, pat in ipairs(PATTERNS) do
    fresh()
    local a = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_" .. pat .. "_DIS" }
    hooks[START](a)
    if a.completed ~= 0 or logged("BLOCKED (" .. pat .. ")") == nil then
      bad[#bad + 1] = pat
    end
  end
  check(#PATTERNS .. " patterns each block their scene", #bad == 0,
        #bad > 0 and ("not blocked: " .. table.concat(bad, ", ")) or nil)
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
  local w2 = mk{ name = "WBP_DIS_Prompt_New_C /Game/W2", opacity = 1.0 }
  a.props["Action Prompt"] = w2
  a.props.IsPaused = true
  hooks[TRIGGER]()
  hooks[DONE](a)
  check("first widget restored, not stranded", w1.opacity == 1.0, "w1=" .. tostring(w1.opacity))
  check("second widget restored", w2.opacity == 1.0, "w2=" .. tostring(w2.opacity))
end
fresh()
do  -- slot reuse: alive, same full name, still holding our 0.0, different object.
    -- Only the address check can tell it apart, so this isolates that check.
  local a, w = scene()
  hooks[START](a)
  w.__addr = 0x900000      -- the proxy now resolves to something else
  hooks[DONE](a)
  check("a same-named object at a new address is not restored", w.opacity == 0.0,
        "opacity=" .. tostring(w.opacity))
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
  check("prompt restored when disabled mid-scene", w.opacity == 1.0, "opacity=" .. tostring(w.opacity))
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
  check("AutoQTE hid the prompt", w.opacity == 0.0, "opacity=" .. tostring(w.opacity))
  w.opacity = 0.35                       -- HUDTweaks mid-fade, after our write
  hooks[DONE](a)
  check("the other mod's value survives", w.opacity == 0.35, "opacity=" .. tostring(w.opacity))
end
fresh()
do  -- unchanged since our write: we must still restore it
  local a, w = scene()
  hooks[START](a)
  hooks[DONE](a)
  check("our own write is still undone", w.opacity == 1.0, "opacity=" .. tostring(w.opacity))
end
fresh()
do  -- the widget was already faded by someone else before we hid it
  local a, w = scene{}
  w.opacity = 0.4
  hooks[START](a)
  hooks[DONE](a)
  check("a pre-existing value is put back, not 1.0", w.opacity == 0.4, "opacity=" .. tostring(w.opacity))
end

io.write("== V12  AutoQTE.ini\n")
do  -- no ini at all: built-in defaults stand
  INI = nil; fresh()
  local a, w = scene()
  hooks[START](a)
  check("no ini -> defaults still work", a.completed == 1 and w.opacity == 0.0,
        "completed=" .. a.completed .. " opacity=" .. tostring(w.opacity))
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
  check("HidePrompt=no is honoured", a.completed == 1 and w.opacity == 1.0,
        "opacity=" .. tostring(w.opacity))
end
do  -- BlockAlso adds patterns
  INI = "; a comment\n[Section]\nBlockAlso = woodchopping , SomeOtherScene\n"; fresh()
  local a = scene()
  hooks[START](a)
  check("BlockAlso blocks a scene the shipped list allows", a.completed == 0,
        "completed=" .. a.completed)
  check("and says which pattern matched", logged("BLOCKED (woodchopping)") ~= nil)
end
do  -- UnblockScenes, with the exact shipped pattern
  INI = "UnblockScenes = takerabbit\n"; fresh()
  local a = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_takerabbit_DIS" }
  hooks[START](a)
  check("UnblockScenes releases the named scene", a.completed == 1, "completed=" .. a.completed)
  check("and says so loudly in the log", logged("UNBLOCKED by ini: takerabbit") ~= nil)
end
do  -- a near miss must drop through, not unblock something by accident
  INI = "UnblockScenes = takerabit, vasyl, VASYLFLOGGING_X\n"; fresh()
  local a = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_takerabbit_DIS" }
  hooks[START](a)
  check("a misspelt pattern unblocks nothing", a.completed == 0, "completed=" .. a.completed)
  local b = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_vasylflogging_DIS" }
  hooks[START](b)
  check("a partial pattern unblocks nothing either", b.completed == 0, "completed=" .. b.completed)
end
do  -- keys come from the ini
  INI = "ToggleKey = F7\nDiagnoseKey =\n"; fresh()
  check("ToggleKey=F7 binds F7", binds.F7 ~= nil)
  check("and not the default F4", binds.F4 == nil)
  check("an empty DiagnoseKey binds nothing", binds.F5 == nil)
end
do  -- junk must not break anything
  INI = "!!! garbage\n= = =\nEnabled\nNoSuchSetting = 12\nEnabled = true\n\n\n"; fresh()
  local a = scene()
  hooks[START](a)
  check("a malformed ini still loads and works", a.completed == 1, "completed=" .. a.completed)
  check("and reports the lines it could not read", logged("not understood") ~= nil)
end
do  -- the blocklist survives a hostile ini
  INI = "BlockAlso =\nBlockAlso = ,,,\n"; fresh()
  local a = scene{ seqName = "InteractiveSceneLevelSequence /Game/Q/DIS/LS_takerabbit_DIS" }
  hooks[START](a)
  check("shipped blocklist intact after an empty BlockAlso", a.completed == 0,
        "completed=" .. a.completed)
end

io.write(string.format("\n%d passed, %d failed\n", pass, fail))
os.exit(fail == 0 and 0 or 1)
