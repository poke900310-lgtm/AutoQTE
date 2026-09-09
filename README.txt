================================================================================
AutoQTE v1.0.0  -  The Blood of Dawnwalker
An UNOFFICIAL fan-made mod. Not affiliated with or endorsed by Rebel Wolves.
Auto-resolves quick-time prompts in Dialogue Interaction Scenes.
================================================================================

WHAT IT DOES

The game's quick-time prompts live in a system it calls DIS ("Dialogue
Interaction Scene") - chopping wood, digging, prying boards, turning a wheel.
AutoQTE resolves them for you by calling the scene's own CompleteCurrentPrompt()
- the exact function the game runs when you hit the prompt yourself - and fades
the prompt ring out so the moment plays through uninterrupted.

18 of the game's 59 DIS scenes are DELIBERATELY LEFT ALONE. Where the prompt is
an act with story weight rather than a chore - harming a named NPC, medical or
ritual scenes, destructive acts - you still perform it yourself. A scene the mod
cannot positively identify is also left alone, on purpose.

It is a Lua-only UE4SS mod: one script, no DLL, no pak, no assets. Two files.
See CONFLICTS below for exactly what it hooks.


--------------------------------------------------------------------------------
REQUIREMENTS
--------------------------------------------------------------------------------

A Dawnwalker-compatible UE4SS 3.x install.

Stock UE4SS cannot detect this game's engine version, so use one of the
Dawnwalker-prepared UE4SS packages from this game's Nexus page (search "UE4SS")
and follow its own instructions - they already ship the correct engine-version
override and hook settings.

AutoQTE needs no hook changes beyond whatever your UE4SS package already does.
Its four hooks are native and run on UE4SS's stock defaults.

If you configured UE4SS yourself, you need:

    [EngineVersionOverride]
    MajorVersion = 5
    MinorVersion = 5

and, unless your UE4SS package ships a build-matched signature file for it:

    [Hooks]
    HookProcessLocalScriptFunction = 0

On this game UE4SS's automatic detector for that function resolves to a
stack-check routine, and hooking it crashes the game at startup - before any mod
loads. If the game crashes on launch immediately after installing UE4SS, that is
the cause, not this mod.

No other mods are required. AutoQTE uses no shared library and depends on
nothing but UE4SS itself.

NOTE: the available UE4SS packages for this game are NOT interchangeable. They
ship different hook settings, and at least one ships a modified UE4SS.dll with
altered Lua behaviour. Do not merge them - back up and replace wholesale. This
mod was developed against a settings-only UE4SS 3.x (build 527a483b) with the
minimal hook set, and it tolerates either DLL variant.


--------------------------------------------------------------------------------
INSTALL
--------------------------------------------------------------------------------

VORTEX
    Install the archive and choose the "UE4SS (Lua mods)" mod type, then enable
    and deploy. Vortex strips the Data folder and deploys into the right place.

MANUAL
    Copy the folder   Data\AutoQTE   from this archive into:

        <Game>\Dawnwalker\Binaries\Win64\ue4ss\Mods\

    so that you end up with:

        ...\ue4ss\Mods\AutoQTE\enabled.txt
        ...\ue4ss\Mods\AutoQTE\Scripts\main.lua
        ...\ue4ss\Mods\AutoQTE\Scripts\AutoQTE.defaults.ini

    Copy AutoQTE.defaults.ini to AutoQTE.ini beside it if you want to change
    a setting. The mod runs fine without it.

    That is the whole mod. Do not copy README.txt or LICENSE.txt into the game
    folder - they are documentation only.

You do NOT need to edit mods.txt. The enabled.txt file is enough on its own, and
shipping a mods.txt would overwrite your load order.


UNINSTALL
    Remove it in Vortex and deploy, or delete the Mods\AutoQTE folder. That
    removes the mod, its settings and its log entirely. Nothing else is
    left behind - AutoQTE writes no file outside its own folder.


--------------------------------------------------------------------------------
CONTROLS
--------------------------------------------------------------------------------

  F4    toggle the mod on/off. Works mid-scene in both directions: turn
        it off and the current prompt comes back for you to play, turn
        it on again and the next prompt in that same scene is resolved.
  F5    print diagnostics for the current scene

Configurable at the top of main.lua:

    Keys = { Toggle = "F4", Diagnose = "F5" },

Any key name UE4SS knows; "" disables that bind. F4 and F5 were chosen because
nothing else in this game's mod ecosystem was found using them. Claimed by other
mods for this game: F1, F2, F3 (DawnWALKING), F6 (UE4SS Cheat Menu, Vampire Form
Toggle), F7/F8/F9/F10 (HUDTweaks - Fixes).

If another mod claims your key first, AutoQTE does NOT take it - it says so in
the log and leaves that bind unregistered, so the other mod keeps working. Pick
a different name and reload.


--------------------------------------------------------------------------------
SETTINGS
--------------------------------------------------------------------------------

Settings live in AutoQTE.ini, beside main.lua in the Scripts folder.

AutoQTE.defaults.ini ships as a commented reference and IS replaced whenever
you update the mod. Copy it to AutoQTE.ini and edit that instead - AutoQTE.ini
is never shipped and never overwritten, so your settings survive updates.
If neither file exists the built-in defaults are used.

Settings are read once at startup. Restart the game after editing.

  Enabled              Master switch. The toggle key flips it in game.
  HidePrompt           Fade the prompt ring while a scene is skipped.
  ToggleKey            Default "F4". Empty binds nothing.
  DiagnoseKey          Default "F5". Empty binds nothing.
  BlockAlso            Extra scenes to leave alone, comma separated.
  UnblockScenes        Shipped entries to release, comma separated. Needs the
                       exact pattern, so a near miss releases nothing, and
                       every release is written to the log.
  Verbose              Also write AutoQTE.log beside main.lua.
  LogEveryCompletion   One line per prompt. Noisy; for diagnosing one scene.

The same values also appear in the Config table at the top of main.lua, which
is what the ini overrides.

  DIS.Enabled          Master switch for the auto-resolve behaviour.

  DIS.HidePrompt       Fade the prompt ring out so nothing flashes on screen.
                       Default true. Purely cosmetic; the prompt is resolved
                       either way.

  BlockedScenes        The safety list: 13 patterns covering 18 scenes. Each
                       entry is a lowercase substring matched against the
                       scene's actor path and its level sequence path, with a
                       comment recording why that scene is on the list. Add
                       your own freely.

  Keys                 Keybinds, see CONTROLS.

  Verbose              Default false. Set true to also write AutoQTE.log next
                       to main.lua. Output always reaches UE4SS.log regardless.

  LogEveryCompletion   Default false. Set true for per-prompt tracing when
                       diagnosing a scene that misbehaves.

NOTE: your settings live inside main.lua, so UPDATING THE MOD OVERWRITES THEM.
Back up main.lua first if you have edited the blocklist or keys.


--------------------------------------------------------------------------------
WHAT IT DOES NOT DO
--------------------------------------------------------------------------------

It never writes to your saves, settings, stats, inventory, quest flags, combat
state, or player state. It simulates no keypresses. It ships no assets and
touches no .pak.

Everything it writes is runtime scene state that the game itself clears when the
scene ends, and the values it writes are identical to the ones the game writes
when you complete a prompt normally.

Most DIS scenes are chores: the outcome is fixed by the sequence reaching its
end, so resolving a prompt early only changes how long you wait. A few are not.
Some prompts are an act with a consequence, and those are exactly what the
safety list above exists for - see BLOCKED SCENES. Either way AutoQTE writes
only the values the game itself writes when you complete a prompt by hand, and
it cannot corrupt a save.

Achievements are not affected. Removing the mod mid-playthrough is safe: it
writes nothing that persists into a save, so there is nothing to undo. Even so,
back up %LOCALAPPDATA%\Dawnwalker\Saved\SaveGames\ before adding any mod.

Not covered, deliberately: hold-to-interact on doors and containers, the
blood-drinking hold, parry and finisher timing, and the Inspection system. None
of those are quick-time prompts, and auto-resolving several of them would have
real consequences.


--------------------------------------------------------------------------------
CONFLICTS
--------------------------------------------------------------------------------

Filenames cannot tell you whether two mods conflict. What matters is what they
hook and what they replace. AutoQTE declares all of it:

  Hooks (native, 4):
      /Script/DogwoodWorld.InteractiveSceneObject:OnInteractiveScenePlaybackStarted
      /Script/DogwoodWorld.InteractiveSceneObject:OnCompletedInteractiveSceneNotification
      /Script/DogwoodWorld.InteractiveSceneObject:OnCancelledInteractiveSceneNotification
      /Script/DogwoodWorld.DISLevelSequenceDirector:TriggerDISInteraction

  Keys:   F4, F5 - yielded to whoever registered them first.

  Assets: NONE. AutoQTE writes no .pak, .utoc or .ucas, replaces no asset,
          and adds no file inside the game's content. It therefore cannot
          conflict with any asset-replacing mod, at any load order.

  Widget: one, and only while a scene is being skipped. With
          DIS.HidePrompt = true (the default) AutoQTE sets RenderOpacity on
          the live WBP_DIS_Prompt_New_C prompt widget and puts it back when
          the scene ends. It only ever undoes its OWN write - if another mod
          changed that value in the meantime, that mod's value stands.

No other mod found for this game hooks those four functions, and AutoQTE
deliberately stays off /Script/Engine.PlayerController:ClientRestart, which
several mods for this game do share. It has no load-order requirement.

HUD mods that manage the DIS prompt widget:

  Dawnwalker HUDTweaks - Fixes lists WBP_DIS_Prompt_New_C in its own fade
  watch list and writes RenderOpacity to it, so both mods end up managing one
  widget. AutoQTE will not overwrite a value HUDTweaks set, which makes the
  usual outcome harmless. If the prompt ever ends up faded when it should not
  be, set DIS.HidePrompt = false here, or drop WBP_DIS_Prompt_New_C from
  HUDTweaks' watch list. Either one settles it.

  Quiet Dawn HUD uses the same capture-and-restore idiom on HUD widgets but
  does not currently target the DIS prompt.

Prerequisite conflicts, which are NOT mod conflicts:

  Two different Dawnwalker UE4SS packages will fight over dwmapi.dll,
  UE4SS-settings.ini and Mods\mods.txt. Install ONE UE4SS package and put
  mods on top of it. AutoQTE ships none of those files and never will.

Input remaps do not matter. AutoQTE never simulates a keypress - it calls the
scene's own CompleteCurrentPrompt - so controller vs keyboard, and any
Enhanced Input remap such as Controller Tweaks & Remap, are irrelevant to it.

If all four hooks cannot be registered, the ones that succeeded are unregistered
again rather than being left attached to functions other mods may hook later.


--------------------------------------------------------------------------------
KNOWN ISSUES THAT ARE NOT THIS MOD
--------------------------------------------------------------------------------

  * UE4SS itself can cause a periodic ~2 second CPU stutter in this game, with
    no mods loaded at all. If you have stutter, test with the loader present
    but every mod removed before blaming any single mod.

  * Some other mods for this game are known to crash at cutscene boundaries.
    If you crash entering or leaving a cinematic, bisect your mod list.

  * A crash at startup, before anything loads, is almost always a UE4SS hook
    setting - see REQUIREMENTS - not a Lua mod.

  * Linux / Proton / Steam Deck: UE4SS needs this Steam launch option:
        WINEDLLOVERRIDES="dwmapi=n,b" %command%

  * Install and remove mods with the game closed. There is no hot reload.


--------------------------------------------------------------------------------
GAME VERSION
--------------------------------------------------------------------------------

Verified on:  dw1-pc-256181-shipping-patch2-all-CL-256181  (UE 5.5.4)
              dw1-pc-257186-shipping-patch2-all-CL-257186  (UE 5.5.4)

The mod identifies everything by NAME, not by memory address, so it is not tied
to a storefront and should carry across builds. If a game update renames the
classes or properties it reads, it stops working SAFELY: it fails closed,
prompts revert to being played by hand, and nothing is auto-resolved.

The blocklist matches asset path substrings, so renamed scene assets would stop
matching. That is why the scene identity is written to the log on every scene.


--------------------------------------------------------------------------------
TROUBLESHOOTING
--------------------------------------------------------------------------------

Look in ue4ss\UE4SS.log (or AutoQTE.log with Verbose = true). Lines there are
prefixed [Lua] [AutoQTE].

  If ue4ss\UE4SS.log does not exist at all
        UE4SS is not installed or is not loading. Nothing below applies.

  "AutoQTE v1.0.0 loaded (15 patterns / 20 scenes blocked)"
        The mod loaded. If this line is missing, it did not.

  "hooked ..."  x4
        Normal. All four hooks registered at startup.

  "FAILED to hook ..."
        A game update changed the scene API. The mod disables itself.

  "skipped: <path>"
        One per auto-resolved scene. This is the line to grep for if you
        want a record of everything the mod did on a playthrough.

  "CompleteCurrentPrompt was refused - left to the player: <path>"
        The mod hid the prompt, asked the game to complete it, and the call
        did not go through - so it restored the prompt and let go of the
        scene. Play that one by hand. If it happens on every scene, a game
        update changed BP_DIS_C; please report the build.

  "ignoring an interactive scene of an unexpected class: <name>"
        The mod saw an interactive scene it does not recognise and left it
        alone. Worth reporting - it means a QTE this mod cannot handle.

  "scene started (playback started): <path>"
  "scene ended (completed) - dormant"
        Normal. One pair per scene.

  "BLOCKED (<name>) - left to the player: <path>"
        Working as intended - that scene is on the safety list. Play it
        yourself.

  "BLOCKED (unidentified scene)" on EVERY scene
        The mod cannot resolve scene identities, so it is refusing to touch
        anything. Safe, but nothing will be auto-resolved. Please report it.

  "F4 is already claimed by another mod - not binding"
        A keybind collision. The other mod keeps the key; AutoQTE binds
        nothing. Change Keys at the top of main.lua.

  "F4 is not a key name UE4SS knows - not binding"
        Typo in Keys. Use a UE4SS key name, e.g. "F4", "HOME", "NUM_LOCK".

  "could not check whether F4 is free - not binding"
  "F4 could not be bound on this UE4SS build"
        The keybind API did not answer, or refused the bind. AutoQTE leaves
        the key alone rather than risk taking it from another mod. The
        auto-resolve behaviour is unaffected; only the key is missing.

  "this UE4SS build has no <name> - AutoQTE disabled"
        The UE4SS you installed does not expose a function this mod needs.
        Use one of the Dawnwalker-prepared UE4SS packages - see REQUIREMENTS.

  Nothing logged when a prompt appears
        The mod is not seeing the scene. Check the four "hooked" lines are
        present and that the mod is enabled (F4).

  A prompt appears and cannot be completed
        Press F4 to disable the mod and play it normally, then report it.


If you report a problem, please include: ue4ss\UE4SS.log, your game build
(right-click Dawnwalker.exe, Details, File version), which UE4SS package and
version you use, and your full list of enabled mods. The Unreal crash dialog on
its own does not contain what is needed to diagnose a mod issue.


--------------------------------------------------------------------------------
AFTER A GAME UPDATE
--------------------------------------------------------------------------------

  1. Launch and confirm the "AutoQTE ... loaded" line and four "hooked" lines.
  2. Play one ordinary scene - expect "scene started" then "scene ended
     (completed)".
  3. Play one blocklisted scene - expect "BLOCKED (...)".
  4. Confirm you do NOT see "BLOCKED (unidentified scene)" everywhere.

If a patch adds quests, the blocklist may need revisiting.

If the game crashes after an update, suspect your UE4SS package before this
mod. Some packages pin themselves to a specific game build and must be updated
when the game is. This mod resolves everything by name and is not build-pinned.


--------------------------------------------------------------------------------
LICENSE
--------------------------------------------------------------------------------

MIT. See LICENSE.txt. Nothing in this mod is derived from another project; its
only dependency is UE4SS, which is not bundled.
