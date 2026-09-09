# AutoQTE — The Blood of Dawnwalker

Auto-resolves the game's DIS quick-time prompts (the button-press and
tap-repeatedly interactions) so they play out on their own, while leaving
story-relevant ones alone for you to perform yourself.

- **Version:** 1.0.0
- **Game:** The Blood of Dawnwalker — verified on `dw1-pc-256181-shipping-patch2-all` (CL-256181) and `dw1-pc-257186-shipping-patch2-all` (CL-257186), both UE 5.5.4
- **Requires:** a Dawnwalker-compatible [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) 3.x install, already working
- **Type:** Lua mod. No pak, no asset replacement, no Blueprint hooks, no shared library.
- **Touches:** nothing outside its own mod folder. No saves, no game settings, no other mod's files.

---

## Install

You need UE4SS running on Dawnwalker first. Stock UE4SS does not work on this
game — use one of the prepared Dawnwalker UE4SS packages from Nexus, which
already carry the engine-version override and the corrected hook set. If the
game launches and `Dawnwalker\Binaries\Win64\ue4ss\UE4SS.log` is being written,
you are ready.

**Vortex:** install the archive and choose the **UE4SS (Lua mods)** install
type. Vortex strips the `Data` folder and deploys into
`Dawnwalker\Binaries\Win64\ue4ss\Mods`.

**Manual:** copy the `AutoQTE` folder out of `Data\` in the archive into
`Dawnwalker\Binaries\Win64\ue4ss\Mods\`, so you end up with:

```
Dawnwalker\Binaries\Win64\ue4ss\Mods\AutoQTE\
    enabled.txt
    Scripts\main.lua
    Scripts\AutoQTE.defaults.ini
```

Copy `AutoQTE.defaults.ini` to `AutoQTE.ini` in that same folder if you want to
change a setting. The mod runs fine without it.

Then start the game. Nothing else needs editing — `enabled.txt` is all UE4SS
needs to start the mod.

The archive ships **no** `UE4SS-settings.ini`, **no** `mods.txt`, **no** pak and
**no** loader files, so installing it cannot overwrite your UE4SS configuration
or your load order.

### If UE4SS is not yet set up for this game

Two settings in `Dawnwalker\Binaries\Win64\ue4ss\UE4SS-settings.ini` are
Dawnwalker requirements, not AutoQTE ones. A prepared Dawnwalker UE4SS package
sets them for you; if you rolled your own, set them yourself:

```ini
[EngineVersionOverride]
MajorVersion = 5
MinorVersion = 5
```

Stock UE4SS cannot detect this build's engine version. Without the override,
object layouts are read wrong and mods behave erratically.

```ini
[Hooks]
HookProcessLocalScriptFunction = 0
```

**The game crashes shortly after the main menu with this at 1**, unless your
UE4SS package supplies a Dawnwalker-specific signature for that function. The
compiler inlined the function on this executable, so UE4SS's generic detector
resolves it to `__security_check_cookie`; detouring that recurses and takes the
process down.

AutoQTE runs on the UE4SS defaults for everything else
(`HookUObjectProcessEvent = 1`, `HookEngineTick = 1`) and needs **nothing turned
off**, so leave the rest of `[Hooks]` exactly as your UE4SS package shipped it.
Mods that need Blueprint hooking keep working alongside it.

## Uninstall

Remove the mod in Vortex, or delete
`Dawnwalker\Binaries\Win64\ue4ss\Mods\AutoQTE\`. That is the whole uninstall.
Nothing is written anywhere else, and no save data is affected — scenes AutoQTE
completed are indistinguishable from scenes you completed by hand, so existing
saves stay valid.

To turn it off without uninstalling, delete `enabled.txt`, or press the toggle
key in-game.

---

## What it does

Dawnwalker's DIS (Dialogue Interaction Scene) system pauses a scripted sequence
and waits for a button press or a tap-repeatedly prompt before continuing.
AutoQTE hooks four **native** engine functions on the scene object and, when a
prompt goes pending, calls the game's own `CompleteCurrentPrompt` and hides the
prompt widget. The scene then continues exactly as if you had pressed the button
on time.

- It uses the game's own completion path. It does not inject input, patch
  memory, or modify assets.
- It only ever resolves a prompt in the direction the game already treats as
  success: it calls the scene's own `CompleteCurrentPrompt`, which is what fires
  `OnPromptSuccess`.
- It is idle when no DIS scene is running. The hooks fire only on scene
  start/complete/cancel and on the prompt trigger.

## What it does *not* do

Each of these was examined and deliberately left alone:

| System | Why it is untouched |
|---|---|
| Hold-to-interact (doors, chests, loot) | Not a QTE, and the underlying getters fire for anything merely focused and in range — automating it would trigger interactables you walk past. |
| Drink Blood | Hold duration decides unconscious vs. drained. That feeds the innocent-kill counter and a persistent fact tag. Your call, not the mod's. |
| Parry | Ordinary combat timing. No prompt exists. |
| Finishers | No input window at all — success is rolled before the animation. Nothing to skip. |
| Inspections | Structurally similar to DIS, but self-paced with no timer and no fail state, and each hotspot plays narrative VO. Automating it would skip content. |

## The blocklist, and why it exists

Not every prompt is a chore. Some of them *are* the scene: the game asks you to
press the button because pressing it is an act with a consequence — hurting
someone, feeding someone, breaking something, performing a ritual on yourself.
Automating those takes the decision away from you, and can quietly change what a
scene means or which of two outcomes you get.

So AutoQTE ships with **13 blocklist entries covering 18 of the game's 59 DIS
scenes**. Blocked scenes are left completely untouched: the prompt
appears, the timer runs, and you play it. The log records
`BLOCKED (<entry>) - left to the player` when one comes up.

The current list, grouped by why:

- **Violence or harm toward a named NPC** — `vasylflogging`, `feedingesme`,
  `forcefeed`.
- **Medical / bodily** — `anca_wounds`, `patching_marat`.
- **Ritual / self-harm / vampiric** — `endurance_trial`, `breakritual`,
  `eating_mandrake`.
- **Destructive or irreversible acts** — `takerabbit`, `destroying_skates`,
  `filling_grave`.
- **Conservative — no in-scene consequence found, kept anyway** —
  `ringingbells`, `gettingkey`.

Entries are matched as **lowercase substrings** against the scene actor's full
name joined with its level sequence's full name. Each entry was checked against
all 59 director-confirmed DIS sequences and all 22,748 level names, and matches
only its intended scenes.

---

## Configuration

Settings live in **`AutoQTE.ini`**, beside `main.lua` in the `Scripts` folder.

`AutoQTE.defaults.ini` ships as a commented reference and **is replaced on
update**. Copy it to `AutoQTE.ini` and edit that — `AutoQTE.ini` is never
shipped and never overwritten, so your settings survive a mod update. If
neither file exists, the built-in defaults apply. Settings are read once at
startup; restart after editing.

| Setting | Default | Effect |
|---|---|---|
| `Enabled` | `true` | Master switch; the toggle key flips it in game. |
| `HidePrompt` | `true` | Fade the prompt ring while a scene is skipped. Set `false` if a HUD mod also manages that widget. |
| `ToggleKey` / `DiagnoseKey` | `F4` / `F5` | UE4SS key names. Empty binds nothing. |
| `BlockAlso` | *(empty)* | Extra scenes to leave alone, comma separated. |
| `UnblockScenes` | *(empty)* | Shipped entries to release, comma separated. Exact pattern; every release is logged. |
| `Verbose` | `false` | Also write `AutoQTE.log` beside `main.lua`. |
| `LogEveryCompletion` | `false` | One line per prompt. Noisy; for diagnosing one scene. |

The list is a judgement call, not a rule the game exposes — so the ini adjusts
it **in both directions** and you never have to edit Lua. `UnblockScenes` needs
the *exact* shipped pattern, so a near miss releases nothing rather than
something unintended, and each release is written to the log as
`UNBLOCKED by ini: <pattern>`.

Press the diagnose key during any scene to see its identity string in the log;
any distinctive lowercase fragment of that works as a pattern.

### `BlockedScenes`

The list described above. Add a lowercase substring to protect a scene, delete
one to let AutoQTE handle it.

To find the right string for a scene: stand in it, press the **diagnose key**,
and read the `actor:` line the mod logs. Any distinctive lowercase fragment of
that name works. Prefer something long and specific (`vasylflogging`) over
something short (`bell`), which will match scenes you did not intend.

### Keybinds

```lua
Keys = { Toggle = "F4", Diagnose = "F5" },
```

F4 and F5 were picked because almost everything else is taken on this game:

| Key | Claimed by |
|---|---|
| F6 | Cheat Menu (open/close), Vampire Form Toggle |
| F7 | HUDTweaks (reload), CursorFix |
| F8 | HUDTweaks (toggle) |
| F9 | HUDTweaks (scan), Ultrawide Fix |
| F10 | UE4SS console, Ultrawide Fix |
| F11 | Cheat Menu, Ultrawide Fix |
| F12 | Cheat Menu, and Steam's screenshot key |

Each entry is the **name** of a UE4SS key, written as a string — `"F4"`,
`"INSERT"`, `"HOME"`, `"NUM_FIVE"`. Set an entry to `""` to register no bind at
all. Modifier combinations are not supported.

F1, F2 and F3 are claimed by DawnWALKING on this game, so they make poor
alternates; prefer something unused like `"INSERT"` or `"HOME"` if F4 or F5
clash on your setup.

UE4SS's own binds are all `Ctrl` combos and do not collide.

### The rest

| Setting | Default | Effect |
|---|---|---|
| `Enabled` | `true` | Master switch. The toggle key flips it at runtime, in either direction, mid-scene: switch off and the live prompt returns for you to play, switch on and the next prompt in that same scene is resolved. Not persisted — restarting restores this value. |
| `DIS.HidePrompt` | `true` | Hides the prompt widget so it does not flash on screen. |
| `Verbose` | `false` | Also write the mod's log lines to `AutoQTE.log` beside `main.lua`. With this off the same lines still reach the UE4SS console and `UE4SS.log`. |
| `LogEveryCompletion` | `false` | Adds a line per individual prompt plus trigger state. Noisy; for diagnosing one misbehaving scene. |

---

## Compatibility

AutoQTE is built to be a non-event for the rest of your load order:

- **Ships one mod folder.** No shared file is in the archive — no
  `UE4SS-settings.ini`, no `mods.txt`, no `mods.json`, no pak, no `LogicMods`
  content, no `shared\` library. Installing it cannot damage an existing setup.
- **Uses `enabled.txt`, not `mods.txt`.** UE4SS starts mods from `mods.txt`
  *and*, separately, from any mod folder containing an `enabled.txt`. Shipping a
  `mods.txt` would replace your load order with the author's; shipping
  `enabled.txt` starts this mod and leaves your load order untouched.
- **Requires no hook to be disabled**, so mods that need Blueprint hooking are
  unaffected.
- **Hooks four game-specific functions** on `InteractiveSceneObject` and
  `DISLevelSequenceDirector`. Nothing else plausibly hooks those, and if
  something does, both hooks still run — UE4SS chains them.
- **Depends on no shared Lua library** — not `UEHelpers`, not `BPModLoader` —
  so there is no version to keep in step with anything.
- **Warns instead of shadowing** if a keybind is already taken by a mod that
  loaded earlier.
- **Writes to exactly one shared thing**, and only during a skip: `RenderOpacity`
  on the live `WBP_DIS_Prompt_New_C` prompt widget, when `DIS.HidePrompt` is on.
  It only ever undoes its *own* write — if another mod changed that value in the
  meantime, that mod's value stands.
- **Known HUD interaction.** *HUDTweaks – Fixes* lists `WBP_DIS_Prompt_New_C` in
  its fade watch list and writes the same property, so both mods manage one
  widget. Harmless in the usual case; if the prompt ends up faded when it
  shouldn't be, set `DIS.HidePrompt = false` or drop that widget from HUDTweaks'
  watch list. *Quiet Dawn HUD* uses the same idiom but does not target the DIS
  prompt.
- **Input remaps are irrelevant.** AutoQTE never simulates a keypress — it calls
  the scene's own `CompleteCurrentPrompt` — so controller vs. keyboard and any
  Enhanced Input remap (*Controller Tweaks & Remap*) do not affect it.
- **Prerequisite conflicts are not mod conflicts.** Two different Dawnwalker
  UE4SS packages will fight over `dwmapi.dll`, `UE4SS-settings.ini` and
  `mods.txt`. Install one UE4SS package and put mods on top. AutoQTE ships none
  of those files.
- **Conflicts only with another QTE mod** touching the same DIS system. Run one
  or the other.

---

## Troubleshooting

The lines below appear in the UE4SS console, in
`Dawnwalker\Binaries\Win64\ue4ss\UE4SS.log`, and — if you set `Verbose = true` —
in `AutoQTE.log` inside the mod folder. All are prefixed `[AutoQTE]` in the
console.

**Nothing in the log at all; the mod never loaded**
`enabled.txt` is missing, or the folder is in the wrong place. The path must be
`ue4ss\Mods\AutoQTE\Scripts\main.lua`, with the `Scripts` subfolder — a common
manual-install mistake is copying the `Data` folder itself. Confirm UE4SS is
running at all: `UE4SS.log` should exist and be recent.

**`FAILED to hook <name> (...)`**
The function was not found. Almost always the game was patched and the class or
function was renamed, or the engine-version override is missing. Check
`[EngineVersionOverride]` is `5` / `5`. If all four fail, UE4SS is not resolving
game symbols at all — a UE4SS/game-version problem, not an AutoQTE one. If some
hook and some do not, the build has changed and the mod needs re-verifying
against it.

**`AutoQTE v1.0.0 loaded (15 patterns / 20 scenes blocked)` but nothing happens in a scene**
Either the scene is blocklisted — look for a `BLOCKED` line — or it never
started under a class the mod recognises. If you see `scene started` but never
`skipped:`, the prompt is not registering as pending: press the diagnose
key during the prompt and check `IsPaused`. If `IsPaused = false` while a prompt
is visible on screen, that is not a DIS prompt and AutoQTE is not meant to
handle it.

**`BLOCKED (<entry>) - left to the player: <actor>`**
Working as intended: that scene is on the blocklist. If you want it automated,
remove the named entry from `BlockedScenes`.

**`BLOCKED (unidentified scene)`**
The mod could not read the scene's level sequence, so it could not tell whether
the scene is blocklisted — and it refuses to automate a scene it cannot
identify. This is the safe failure. It usually means a game patch changed
`GetInteractiveSceneLevelSequence`. Play that prompt manually, and report the
build.

**`scene started (playback started)` … `scene ended (completed) - dormant`**
Normal. That is one scene handled end to end.

**`trigger fired but no scene tracked`**
A prompt fired for a scene the mod is not following — usually a blocklisted one
(expected), or a scene already running when the mod loaded. Harmless.

**`CompleteCurrentPrompt was refused - left to the player: <scene>`**
The mod hid the prompt, asked the game to complete it, and the call did not go
through — so it put the prompt back and let go of the scene. You play that one
by hand. If it happens on every scene, a game patch changed `BP_DIS_C` and the
mod needs re-verifying against the new build.

**`could not check whether F4 is free - not binding`** / **`F4 could not be bound on this UE4SS build`**
The keybind API did not answer, or refused the bind. AutoQTE leaves the key
alone rather than risk taking it from another mod. Auto-resolving still works;
only the key is missing.

**`F4 is already claimed by another mod - not binding; change Config.Keys`**
Exactly what it says. Pick a different key in the `Keys` table. This check only
sees mods that loaded before AutoQTE, so a silent clash with one that loads
later is still possible — if a key does nothing, change it.

**Prompt widget stays invisible after a scene**
Set `DIS.HidePrompt = false`. Widget opacity is restored when a scene ends, and
a restore the engine refuses no longer poisons the stored value — but if a scene
is torn down abnormally the restore can still be missed. Cosmetic and
per-session; reloading a save clears it.

**Game crashes on launch or shortly after the main menu**
Not AutoQTE — remove it and confirm. The usual cause on this game is
`HookProcessLocalScriptFunction = 1` without a Dawnwalker-specific signature.

---

## Known limitations

- **Verified on two builds, pinned to neither.** Everything is resolved by name
  and never by address, so the mod is not tied to a storefront or a build
  number — confirmed on CL-256181 and CL-257186, both UE 5.5.4 / patch2. What a
  patch *can* break is the names themselves: the four hooked functions and the
  blocklist substrings come from that object graph, and the mod then needs
  re-verification.
- **Failure is quiet and safe.** If a hook cannot be installed, or a scene cannot
  be identified, AutoQTE does nothing and the game behaves normally. It never
  falls back to guessing.
- **The blocklist is a judgement call.** It reflects one person's reading of
  which prompts carry weight. Yours may differ — edit it.
- **No on-screen indication.** A skipped scene is recorded in the log, not on
  screen. An on-screen notice was built and tested against the shipping build:
  the only suitable widget the game ships is not loaded during open-world play,
  so it could never appear, and it was removed rather than left in as dead code.
- **No console commands.** `ProcessConsoleExec` is unavailable in this title, so
  configuration is by editing the file plus the two keybinds.

## After a game update

Re-check in this order before trusting the mod on a new build:

1. Game still launches with UE4SS attached.
2. All four `hooked …` lines appear in the log. Any `FAILED to hook` means a
   class or function was renamed — stop here.
3. Enter one ordinary, non-blocklisted DIS scene. Expect `scene started`,
   `skipped:`, `scene ended (completed)`.
4. Enter one blocklisted scene. Expect `BLOCKED (<entry>)` and a live prompt you
   have to play yourself.
5. Watch for `BLOCKED (unidentified scene)` anywhere. One occurrence means scene
   identification broke and the blocklist is no longer protecting anything — the
   mod is failing safe, but it is failing.
6. If the patch added quests or scenes, re-derive the DIS scene list and re-audit
   the blocklist rather than assuming the old 59 still hold.

## Development

The mod is a single file: `Scripts/main.lua`. There is nothing to compile.

```
Scripts/main.lua              the mod
enabled.txt                   zero-byte marker UE4SS looks for
README.txt / LICENSE.txt      shipped at the archive root
tests/autoqte_regression.lua  regression suite
tests/mutants.py              proves the suite can actually fail
tools/build.py                assembles dist/AutoQTE.zip
```

Run the suite against any copy of the mod — a working tree, or the file in a
live install:

```
lua54.exe tests/autoqte_regression.lua Scripts/main.lua
```

It stubs the UE4SS globals, including the truthy-phantom behaviour for members
that do not exist, and asserts only on observables: whether
`CompleteCurrentPrompt` was called, on what, what was logged, and what opacity
the prompt widget was left at.

A green suite means nothing on its own, so every assertion is mutation-tested:

```
python tests/mutants.py <path to lua54.exe>
```

Each mutant breaks one behaviour and the suite must go red. Any `SURVIVED` line
is a hole. One known survivor is documented in that script and deliberately
excluded — `getScalar`'s type filter is guarded again by every caller, so
removing it changes no observable.

To check whether another mod can conflict, point this at its release archive
or its `package/` directory — not a source checkout, since mod repos often
vendor a copy of another mod:

```
python tools/check_conflict.py <mod.zip>
```

It reports whether the mod hooks the DIS system, writes the prompt widget,
binds F4/F5, or ships a shared UE4SS file. Those are the only four ways
anything can collide with AutoQTE; everything else is compatible at any load
order.

To build the release archive:

```
python tools/build.py
```

It refuses to package a file with `Verbose` or `LogEveryCompletion` left on.

## Credits and licence

AutoQTE is original work. It contains no code from another mod or project, and
depends on no UE4SS shared library. It requires
[UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) at runtime but bundles none of it
— install UE4SS separately.

Released under the MIT Licence; see `LICENSE.txt`.

The Blood of Dawnwalker is © Rebel Wolves. This mod is unaffiliated and
unofficial, and ships no game assets.
