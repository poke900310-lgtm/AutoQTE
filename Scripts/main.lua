-- AutoQTE - The Blood of Dawnwalker
-- Auto-resolves DIS (Dialogue Interaction Scene) prompts.
-- F4 toggle | F5 diagnose   (F10 is the game console, bound by ConsoleEnablerMod)
-- Console commands do not work in this title (ProcessConsoleExec unavailable).

local VERSION = "1.0.2"

local Config = {
    Enabled = true,

    DIS = {
        Enabled = true,
        HidePrompt = true,
    },

    -- Scenes to leave to the player. EMPTY BY DEFAULT.
    --
    -- Auto-completing a prompt is not a story decision. AutoQTE only ever calls
    -- CompleteCurrentPrompt, which fires OnPromptSuccess and sets the scene's end
    -- type to Completed (BP_DIS_C ubergraph 15292) - byte-identical to what the
    -- game records when you press the button yourself. It cannot produce any
    -- other end state.
    --
    -- Quest logic DOES distinguish outcomes: QuestNodeInteractiveScene_Controller
    -- declares OnCompletedInteractiveScene and OnCancelledInteractiveScene, and
    -- InteractiveSceneObject carries a delegate for each. AutoQTE can only ever
    -- reach the Completed side - the same side successful manual play reaches.
    -- EInteractiveSceneEndType's third value, CancelledByPlayer, is never written
    -- by BP_DIS_C at all: only Completed (2) and CancelledByQuestNode (1).
    --
    -- So this list is a matter of TASTE. Use it if you would rather perform a
    -- scene yourself. AutoQTE.defaults.ini carries a ready-made cautious set.
    BlockedScenes = {},

    -- Evaluated and deliberately NOT implemented, each for a validated reason:
    --   ButtonHold  hold-to-interact on doors/chests/loot. Not a QTE, and the
    --               getters fire for anything merely focused and in range, so
    --               forcing them auto-triggers interactables you walk past.
    --   DrinkBlood  hold duration picks unconscious vs drained; that feeds
    --               bCountToInnocentKills and a persistent fact tag.
    --   Parry       ordinary combat timing, no prompt.
    --   Finisher    no input window exists at all -- the success chance is
    --               rolled before the animation, so there is nothing to skip.
    --   Inspection  AInspectableBase, a structural twin of DIS, but self-paced
    --               with no timer and no fail state, and each hotspot fires
    --               narrative VO.

    -- Known claimed in this game: F1/F2/F3, F6, F7, F8, F9, F10. F4 and F5
    -- collide with nothing found here, but both are popular in UE4SS mods
    -- generally, so they are names rather than constants. "" disables.
    Keys = { Toggle = "F4", Diagnose = "F5" },

    Verbose = false,
    -- Per-prompt tracing (trigger state + each completion). Off for normal
    -- play; set true to diagnose a scene that misbehaves.
    LogEveryCompletion = false,
}

local ISO         = "/Script/DogwoodWorld.InteractiveSceneObject"
local HOOK_START  = ISO .. ":OnInteractiveScenePlaybackStarted"
local HOOK_DONE   = ISO .. ":OnCompletedInteractiveSceneNotification"
local HOOK_CANCEL = ISO .. ":OnCancelledInteractiveSceneNotification"
local HOOK_PROMPT = "/Script/DogwoodWorld.DISLevelSequenceDirector:TriggerDISInteraction"

local DIS_CLASS   = "BP_DIS_C"
local P_WIDGET    = "Action Prompt"
local P_PAUSED    = "IsPaused"
local W_ACTIVE    = "IsPromptActive"

-- Beside this script, wherever installed. Never a hardcoded path.
local LOG = (debug.getinfo(1, "S").source:match("^@(.*[/\\])") or "") .. "AutoQTE.log"

local logFile, lastMsg, reps = nil, nil, 0

local function emit(msg)
    print("[AutoQTE] " .. msg .. "\n")
    if Config.Verbose and logFile ~= false then
        if not logFile then
            local okf, f = pcall(io.open, LOG, "a")
            logFile = (okf and f) or false      -- false = tried and failed, never retry
            if not logFile then print("[AutoQTE] could not open " .. LOG .. "\n") end
        end
        if logFile then logFile:write(msg .. "\n"); logFile:flush() end
    end
end

local function log(fmt, ...)
    local ok, msg = pcall(string.format, fmt, ...)
    if not ok then msg = tostring(fmt) end
    if msg == lastMsg then reps = reps + 1; return end
    lastMsg = msg
    if reps > 0 then emit(string.format("(previous line x%d)", reps + 1)); reps = 0 end
    emit(msg)
end

-- Settings live in AutoQTE.ini beside this script, so a mod update cannot
-- overwrite them. AutoQTE.defaults.ini ships as the reference copy and IS
-- replaced on update. Anything absent or unreadable keeps the value above.
-- BlockAlso in the ini is how the blocklist is normally populated at all.
local INI_FILES = { "AutoQTE.ini", "AutoQTE.defaults.ini" }

local function iniBody()
    local dir = LOG:sub(1, #LOG - #("AutoQTE.log"))
    for _, name in ipairs(INI_FILES) do
        local okf, f = pcall(io.open, dir .. name, "r")
        if okf and f then
            local ok, body = pcall(function() return f:read("a") end)
            pcall(function() f:close() end)
            if ok and type(body) == "string" and body ~= "" then return body, name end
        end
    end
end

local function toBool(v)
    v = v:lower()
    if v == "true"  or v == "1" or v == "yes" or v == "on"  then return true  end
    if v == "false" or v == "0" or v == "no"  or v == "off" then return false end
    return nil
end

local function applyIni()
    local body, name = iniBody()
    if not body then
        log("no AutoQTE.ini or AutoQTE.defaults.ini beside main.lua - using built-in defaults")
        return
    end
    body = body:gsub("^\239\187\191", "")            -- a UTF-8 BOM would eat the first setting
    local set, bad = 0, 0
    for line in body:gmatch("[^\r\n]+") do
        -- Collapse whitespace runs first: the trims below are O(n^2) on a long one.
        line = line:gsub("[ \t]+", " ")
        if not line:match("^%s*[;#%[]") then
            -- Accept a dotted key: v1.0.0 documented DIS.HidePrompt.
            local k, v = line:match("^%s*([%w_.]+)%s*=%s*(.-)%s*$")
            if k then
                -- Inline comment only after whitespace: a bare ; or # is part of
                -- the value, so BlockAlso = alpha#beta cannot truncate to alpha.
                v = v:gsub("%s+[;#].*$", ""):gsub("[;#]+$", "")
                local raw = v                                      -- BlockAlso unquotes per item
                v = v:match('^"(.*)"$') or v:match("^'(.*)'$") or v  -- README showed quotes
                local key = k:lower():gsub("^dis%.", "")   -- one name: gsub's count is dropped
                local b = toBool(v)                        -- "" yields nil, same as no value
                if     key == "enabled"            and b ~= nil then Config.Enabled = b;              set = set + 1
                elseif key == "hideprompt"         and b ~= nil then Config.DIS.HidePrompt = b;       set = set + 1
                elseif key == "verbose"            and b ~= nil then Config.Verbose = b;              set = set + 1
                elseif key == "logeverycompletion" and b ~= nil then Config.LogEveryCompletion = b;   set = set + 1
                elseif key == "togglekey"          then Config.Keys.Toggle = v;                       set = set + 1
                elseif key == "diagnosekey"        then Config.Keys.Diagnose = v;                     set = set + 1
                elseif key == "blockalso"          then
                    for pat in raw:gmatch("[^,]+") do
                        pat = pat:match("^%s*(.-)%s*$")
                        -- per item: a whole-value unquote turns '"a", "b"' into junk
                        pat = (pat:match('^"(.*)"$') or pat:match("^'(.*)'$") or pat):lower()
                        if pat ~= "" then
                            Config.BlockedScenes[#Config.BlockedScenes + 1] = pat
                            set = set + 1
                        end
                    end
                else bad = bad + 1 end
            elseif line:match("%S") then
                bad = bad + 1                          -- never drop a line silently
            end
        end
    end
    log("%s: %d setting(s) applied%s", name, set,
        bad > 0 and (", " .. bad .. " line(s) not understood") or "")
end

pcall(applyIni)

local function isAlive(obj)
    if not obj then return false end
    local ok, v = pcall(function() return obj:IsValid() end)
    return ok and v
end

-- UE4SS returns a truthy userdata for members that do not exist, so a bare
-- read cannot tell "false" from "no such property". Only scalars are trusted.
local function getScalar(obj, name)
    local ok, v = pcall(function() return obj[name] end)
    if not ok then return nil end
    local t = type(v)
    if t == "boolean" or t == "number" or t == "string" then return v end
    return nil
end

local function getObject(obj, name)
    local ok, v = pcall(function() return obj[name] end)
    if ok and isAlive(v) then return v end
    return nil
end

local function call(obj, name, ...)
    local args = { ... }
    local ok, res = pcall(function() return obj[name](obj, table.unpack(args)) end)
    return ok, res
end

local function fullName(obj)
    local ok, n = pcall(function() return obj:GetFullName() end)
    if ok and type(n) == "string" then return n end
    return ""
end

-- Two Lua proxies for one UObject are never == equal; compare addresses.
local function sameActor(a, b)
    local ok, eq = pcall(function() return a:GetAddress() == b:GetAddress() end)
    return ok and eq
end

local function addressOf(obj)
    local ok, a = pcall(function() return obj:GetAddress() end)
    if ok and type(a) == "number" then return a end
    return nil
end

local function classOf(obj)
    local ok, n = pcall(function() return obj:GetClass():GetFName():ToString() end)
    if ok and type(n) == "string" then return n end
    return ""
end

local scene          = nil
local seenClass      = {}
local announced      = false
local sceneId        = nil
local hiddenWidget   = nil
local hiddenName     = nil
local hiddenAddr     = nil
local hiddenOpacity  = nil

local endScene

local function sceneIdentity(actor)
    local ok, seq = call(actor, "GetInteractiveSceneLevelSequence")
    if not (ok and isAlive(seq)) then return nil end
    local n = fullName(seq)
    if n == "" then return nil end
    return (fullName(actor) .. " " .. n):lower()
end

local function diagnose(actor)
    log(string.rep("-", 62))
    log("actor: %s", fullName(actor))
    log("scene: %s", sceneIdentity(actor) or "<unidentified>")
    for _, p in ipairs({ P_PAUSED, "PauseElapsedTime", "TappingCount", "TappingStep",
                         "TappingDrop", "Tapping Threshold", "LastTime",
                         "InteractiveSceneEndType" }) do
        local v = getScalar(actor, p)
        if v ~= nil then log("  %-24s = %s", p, tostring(v)) end
    end
    local w = getObject(actor, P_WIDGET)
    if w then
        log("  %-24s = %s", P_WIDGET, fullName(w))
        local a = getScalar(w, W_ACTIVE)
        if a ~= nil then log("  widget.%-17s = %s", W_ACTIVE, tostring(a)) end
    else
        log("  %-24s = <none>", P_WIDGET)
    end
    log(string.rep("-", 62))
end

local function promptPending(actor)
    return getScalar(actor, P_PAUSED) == true
end

local function setOpacity(w, value)
    if not (w and isAlive(w)) then return false end
    return (call(w, "SetRenderOpacity", value))
end

-- Undoes our own write and nothing else. If another HUD mod has touched the
-- widget since we hid it, its value stands -- we do not own that pixel.
local function restorePrompt()
    local restored, prev = true, hiddenOpacity
    if hiddenWidget and isAlive(hiddenWidget)
       and addressOf(hiddenWidget) == hiddenAddr and fullName(hiddenWidget) == hiddenName
       and getScalar(hiddenWidget, "RenderOpacity") == 0.0 then
        restored = setOpacity(hiddenWidget, hiddenOpacity or 1.0)
    end
    -- Only forget the widget if we actually un-hid it. Dropping it after a refusal
    -- strands it at 0.0 for the session and latches that 0.0 as the "original".
    if restored then
        hiddenWidget, hiddenName, hiddenAddr, hiddenOpacity = nil, nil, nil, nil
    end
    return restored, prev
end

local function hidePrompt(actor)
    if not Config.DIS.HidePrompt then return end
    local w = getObject(actor, P_WIDGET)
    local restored, prev = restorePrompt()
    -- A refused restore leaves our own 0.0 on the widget; never latch that as the original.
    local was = getScalar(w, "RenderOpacity")
    if not restored and was == 0.0 then was = prev end
    if setOpacity(w, 0.0) then
        hiddenWidget, hiddenName, hiddenAddr = w, fullName(w), addressOf(w)
        hiddenOpacity = type(was) == "number" and was or 1.0
    end
end

local function isBlocked(id)
    if not id then return "unidentified scene" end
    for _, pat in ipairs(Config.BlockedScenes) do
        if id:find(pat, 1, true) then return pat end
    end
    return nil
end

local function resolvePrompt(actor)
    if not Config.Enabled or not isAlive(actor) then return end
    if not promptPending(actor) then return end

    local id = sceneId
    hidePrompt(actor)
    if not (call(actor, "CompleteCurrentPrompt")) then
        log("CompleteCurrentPrompt was refused - left to the player: %s", id or fullName(actor))
        endScene("completion refused")
        return
    end
    if not announced then
        announced = true
        log("skipped: %s", id or fullName(actor))
    end
    if Config.LogEveryCompletion then log("prompt completed") end
end

local function beginScene(actor, reason)
    -- Track the scene even while the toggle is off, so F4 resumes mid-scene.
    -- Config.Enabled gates the acting, in resolvePrompt; it does not gate the watching.
    if not Config.DIS.Enabled then return end
    if not isAlive(actor) then return end
    local cls = classOf(actor)
    if fullName(actor):find("Default__", 1, true) then return end
    if cls ~= DIS_CLASS then
        if cls ~= "" and not seenClass[cls] then
            seenClass[cls] = true
            log("ignoring an interactive scene of an unexpected class: %s", cls)
        end
        return
    end

    if not sameActor(scene, actor) then endScene("superseded") end

    local id = sceneIdentity(actor)
    local blocked = isBlocked(id)
    if blocked then
        endScene("blocked")
        log("BLOCKED (%s) - left to the player: %s", blocked, id or fullName(actor))
        return
    end

    scene = actor
    sceneId = id
    announced = false
    log("scene started (%s): %s", reason, id)
    resolvePrompt(actor)
end

endScene = function(reason)
    restorePrompt()
    if not scene then return end
    scene = nil
    sceneId = nil
    announced = false
    log("scene ended (%s) - dormant", reason)
end

local hooks = {}

local function unhookAll()
    for _, h in ipairs(hooks) do pcall(UnregisterHook, h[1], h[2], h[3]) end
    hooks = {}
end

local function hook(path, cb, label)
    local noop = function() end
    local ok, pre, post = pcall(RegisterHook, path, noop, cb)
    if ok and type(pre) == "number" and type(post) == "number" and pre ~= post then
        hooks[#hooks + 1] = { path, pre, post }
        log("hooked %s", label)
        return true
    end
    if ok and type(pre) == "number" and pre == post then
        log("FAILED to hook %s (script path - callback would be dropped)", label)
    else
        log("FAILED to hook %s (%s)", label, tostring(pre))
    end
    return false
end

-- Some UE4SS distributions for this game ship a patched DLL that hands hook
-- callbacks the value directly instead of a parameter wrapper. Accept both.
local function contextActor(Context)
    local ok, obj = pcall(function() return Context:get() end)
    if ok and isAlive(obj) then return obj end
    if isAlive(Context) then return Context end
    return nil
end

local MISSING
for _, g in ipairs({ "RegisterHook", "UnregisterHook", "RegisterKeyBind",
                     "IsKeyBindRegistered", "ExecuteInGameThread", "FindAllOf",
                     "Key" }) do
    if rawget(_G, g) == nil then MISSING = g break end
end

if MISSING then
    Config.DIS.Enabled = false
    log("this UE4SS build has no %s - AutoQTE disabled", MISSING)
end

if Config.DIS.Enabled then
    local ok = true
    ok = hook(HOOK_START, function(Context)
        local a = contextActor(Context)
        if a then beginScene(a, "playback started") end
    end, "OnInteractiveScenePlaybackStarted") and ok

    ok = hook(HOOK_DONE, function(Context)
        local a = contextActor(Context)
        if sameActor(a, scene) then endScene("completed") end
    end, "OnCompletedInteractiveSceneNotification") and ok

    ok = hook(HOOK_CANCEL, function(Context)
        local a = contextActor(Context)
        if sameActor(a, scene) then endScene("cancelled") end
    end, "OnCancelledInteractiveSceneNotification") and ok

    ok = hook(HOOK_PROMPT, function()
        if not scene then log("trigger fired but no scene tracked"); return end
        if not isAlive(scene) or classOf(scene) ~= DIS_CLASS then endScene("actor invalid"); return end
        if sceneIdentity(scene) ~= sceneId then endScene("actor is no longer that scene"); return end
        if Config.LogEveryCompletion then
            local w = getObject(scene, P_WIDGET)
            log("trigger: IsPaused=%s widget.IsPromptActive=%s",
                tostring(getScalar(scene, P_PAUSED)),
                tostring(w and getScalar(w, W_ACTIVE) or nil))
        end
        resolvePrompt(scene)
    end, "TriggerDISInteraction") and ok

    if not ok then
        unhookAll()
        Config.DIS.Enabled = false
        log("a hook did not resolve - a game update likely changed the scene API; AutoQTE disabled")
    end
end


local function inGame(fn)
    if not pcall(ExecuteInGameThread, fn) then log("could not reach the game thread") end
end

local function bind(name, fn)
    if type(name) ~= "string" or name == "" then return end
    name = name:upper()
    local ok, key = pcall(function() return Key[name] end)
    if not (ok and type(key) == "number") then
        log("%s is not a key name UE4SS knows - not binding", name)
        return
    end
    local okr, taken = pcall(IsKeyBindRegistered, key)
    if not okr then
        log("could not check whether %s is free - not binding", name)
        return
    end
    if taken then
        log("%s is already claimed by another mod - not binding; change it in AutoQTE.ini", name)
        return
    end
    if not pcall(RegisterKeyBind, key, {}, fn) then
        log("%s could not be bound on this UE4SS build", name)
    end
end

if not MISSING then

bind(Config.Keys.Toggle, function()
    inGame(function()
        Config.Enabled = not Config.Enabled
        if not Config.Enabled then restorePrompt() end
        log("%s", Config.Enabled and ">>> AutoQTE ENABLED" or "<<< AutoQTE DISABLED")
    end)
end)

-- F5 also inspects UNTRACKED actors (blocked scenes, or a scene we never
-- adopted), so a blocklist hit can still be diagnosed. The sweep is expensive
-- but runs only on this keypress, never on a timer.
bind(Config.Keys.Diagnose, function()
    inGame(function()
        if scene and isAlive(scene) then diagnose(scene); return end
        local ok, actors = pcall(FindAllOf, DIS_CLASS)
        local n = 0
        if ok and type(actors) == "table" then
            for _, a in pairs(actors) do
                if isAlive(a) and not fullName(a):find("Default__", 1, true) then
                    if getScalar(a, P_PAUSED) == true then
                        log("untracked actor with a prompt pending:")
                        diagnose(a)
                        n = n + 1
                    end
                end
            end
        end
        if n == 0 then log("dormant - no scene tracked, no pending prompt found") end
    end)
end)

end

log("")
log("AutoQTE v%s loaded (%d blocklist patterns)", VERSION, #Config.BlockedScenes)
