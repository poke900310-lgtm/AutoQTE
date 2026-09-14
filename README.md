# AutoQTE — The Blood of Dawnwalker

I made this mod because devs putting in unnecessary button prompts is the
continuing bane of my existence.

Dawnwalker puts a button prompt in front of a lot of small scenes. AutoQTE
presses it for you. The scene is not skipped and nothing is faked: the mod
calls the game's own `CompleteCurrentPrompt`, the same function your keypress
calls, so the scene ends in the Completed state and every quest node downstream
sees exactly what it expects.

- **Nexus:** <https://www.nexusmods.com/thebloodofdawnwalker/mods/456>
- **Releases:** <https://github.com/poke900310-lgtm/AutoQTE/releases/latest>
- **Version:** 1.0.8 (UE4SS edition) · 1.0.1 (.pak edition)
- **Game:** The Blood of Dawnwalker, UE 5.5.4, verified on Steam build `25232147`

## Editions

| | UE4SS edition (recommended) | .pak edition |
|---|---|---|
| requires | a working Dawnwalker UE4SS install | nothing |
| controls | F4 toggle, INS diagnose, `BlockAlso`, ini, log | none |
| after a game patch | keeps working unless a function is renamed | may need a rebuild |

Both complete the prompt through `CompleteCurrentPrompt` and hide the prompt
widget by setting its `Visibility` to `Collapsed`. Use the UE4SS edition unless
you cannot run UE4SS; install one or the other, not both.

## Install

**UE4SS edition.** Extract the archive into your game folder and merge
`Dawnwalker`, or install it with a mod manager. It carries the full path:

```
Dawnwalker\Binaries\Win64\ue4ss\Mods\AutoQTE\
    enabled.txt
    README.txt
    LICENSE.txt
    Scripts\main.lua
    Scripts\AutoQTE.defaults.ini
```

No `mods.txt` entry is needed. On Xbox / Game Pass the project folder is
`Binaries\WinGDK`; move the `AutoQTE` folder there afterwards. To uninstall,
delete the folder.

**.pak edition.** Extract `AutoQTE-PAK-<version>.zip` into the game folder, or
drop the three `AutoQTE_P.*` files into `Dawnwalker\Content\Paks\`. To
uninstall, delete them.

## Configuration

Settings live in `AutoQTE.ini` beside `main.lua`. It is not shipped: copy
`AutoQTE.defaults.ini` to that name and edit the copy. It survives updates;
the defaults file does not. Settings load at startup.

```ini
Enabled = true
HidePrompt = true
ToggleKey = F4
DiagnoseKey = INS
BlockAlso =
Verbose = false
LogEveryCompletion = false
```

Key names are UE4SS names (`F4`, `INS`, `HOME`, `NUM_FIVE`); an empty value
binds nothing. A UE4SS key fires alongside the game's own binding for that key,
which is why the diagnose key is INS and not F5, the game's quicksave.

## The blocklist

Nothing is blocked by default. A DIS prompt has no failure state, so a scene
AutoQTE completes reaches the same state as one played by hand. What
auto-completion removes is the option to walk away from a scene instead of
performing it; if you want that choice for the game's more pointed moments,
add those scenes to `BlockAlso`. `AutoQTE.defaults.ini` carries a ready-made
set of 13 patterns, commented out. `BLOCKABLE-SCENES.md` lists every scene a
pattern can name.

## Requirements and compatibility

The UE4SS edition needs a Dawnwalker-compatible UE4SS 3.x install; stock UE4SS
cannot detect this game's engine version, so use one of the prepared packages
from Nexus. The mod uses four native hooks and two keybinds, ships no shared
file, and does not touch `dwmapi.dll`, `UE4SS-settings.ini` or `mods.txt`. It
conflicts only with another mod that drives the same DIS prompts. If F4 or INS
is already taken by another mod, AutoQTE says so in the log and does not bind.

The .pak edition conflicts with any mod that overrides `BP_DIS` or
`WBP_DIS_Prompt_New`.

## Disclaimer and reporting bugs

Save often, and keep more than one save. A scene AutoQTE completes is
indistinguishable from one you completed by hand, but the mod removes the
choice *not* to press, and a few scene director graphs do more than hand out a
prompt, so an auto-completed scene is not always something you can take back.
Use it at your own risk; see `LICENSE.txt`.

To report a problem: press **INS** while the scene is on screen, with
`Verbose = true` set beforehand so the lines land in `AutoQTE.log`, and keep a
save from just before the scene if you have one.

---

# Development

```
Scripts/main.lua              the UE4SS edition
AutoQTE.defaults.ini          shipped reference config
enabled.txt                   zero-byte marker UE4SS looks for
README.txt / LICENSE.txt      shipped inside the mod folder
BLOCKABLE-SCENES.md           every scene BlockAlso can name; generated
CHANGELOG.md                  release notes
NEXUS.md                      the Nexus page description
tests/autoqte_regression.lua  regression suite
tests/mutants.py              mutation battery for the suite
tools/build.py                assembles dist/AutoQTE-<version>.zip
tools/pak/                    the .pak edition: patcher, build, scene list
```

## UE4SS edition

`Scripts/main.lua` is a single file with no dependencies beyond UE4SS. It
registers four native hooks and reacts:

| hook | role |
|---|---|
| `InteractiveSceneObject:OnInteractiveScenePlaybackStarted` | adopt the scene, identify it, check the blocklist |
| `DISLevelSequenceDirector:TriggerDISInteraction` | a prompt is pending: hide the widget, call `CompleteCurrentPrompt` |
| `InteractiveSceneObject:OnCompletedInteractiveSceneNotification` | release the scene, restore the widget |
| `InteractiveSceneObject:OnCancelledInteractiveSceneNotification` | same, on cancel |

A scene is identified by the actor's full name joined with its level
sequence's full name; `BlockAlso` patterns are substrings of that string.
Only `BP_DIS_C` actors are handled, and a scene that cannot be identified is
never automated.

The prompt widget (`WBP_DIS_Prompt_New_C`, the actor's `Action Prompt`) is
hidden by `SetVisibility(Collapsed)` and restored to its previous value when
the scene ends. The mod only undoes its own write: if the widget no longer
reads `Collapsed`, another mod changed it and that value stands. Every write is
read back, and a read-back that is unreadable or not a number is treated as no
evidence rather than as a failure.

Every engine call is wrapped in `pcall`, because UE4SS returns truthy phantom
userdata for members that do not exist; only scalar reads are trusted. Live
objects are compared by `GetAddress()` — the prompt widget additionally by its
full name — never by Lua `==`.
If `CompleteCurrentPrompt` is refused or returns without clearing the prompt,
the widget is restored and the scene is handed back to the player.

### UE4SS settings

Two settings in `UE4SS-settings.ini` are requirements of the game, not the
mod; the prepared packages set them:

```ini
[EngineVersionOverride]
MajorVersion = 5
MinorVersion = 5

[Hooks]
HookProcessLocalScriptFunction = 0
```

Without the override, object layouts are read wrong. With the hook enabled
and no Dawnwalker-specific signature, UE4SS detours a stack-check routine and
the game crashes after the main menu. AutoQTE itself needs only the defaults
(`HookUObjectProcessEvent = 1`, `HookEngineTick = 1`).

### Keys

F4 and INS are the defaults because many other function keys are already used by other mods on this game, and F10
is the UE4SS console. The mod refuses a key another UE4SS
mod registered first, but it cannot see the game's own bindings.

### Tests

```
lua54.exe tests/autoqte_regression.lua Scripts/main.lua
python tests/mutants.py <path to lua54.exe>
```

The suite stubs the UE4SS globals, including the phantom-userdata behaviour,
and asserts only on observables: what was called, on what, what was logged,
and what visibility the widget was left at. Every assertion is mutation-tested;
each mutant breaks one behaviour and the suite must go red. Mutation anchors
are literal source snippets, so a reflow of `main.lua` may need them
repointed.

### Reading the log

Lines appear in the UE4SS console, in `UE4SS.log`, and with `Verbose = true`
in `AutoQTE.log` beside `main.lua`.

| line | meaning |
|---|---|
| `hooked …` ×4 | normal startup |
| `FAILED to hook …` | a game update renamed a function; the mod disables itself |
| `scene started …` / `scene ended (completed)` | one scene handled |
| `skipped: <scene>` | one auto-resolved scene; grep for this to see everything the mod did |
| `BLOCKED (<entry>)` | the scene is in `BlockAlso` |
| `BLOCKED (unidentified scene)` | the scene could not be identified and was left alone; report the build |
| `CompleteCurrentPrompt was refused - left to the player` | the call did not go through; the prompt was restored |
| `trigger fired but no scene tracked` | a prompt in a scene the mod is not following; harmless |

### After a game update

1. Confirm the four `hooked` lines.
2. Play one ordinary scene: expect `scene started`, `skipped:`, `scene ended (completed)`.
3. Play one blocklisted scene: expect `BLOCKED`.
4. If `BLOCKED (unidentified scene)` appears, identification broke; the mod is
   failing safe but not working.
5. Regenerate `BLOCKABLE-SCENES.md` and re-check any patterns you added.

## .pak edition

The pak edition overrides two cooked assets so that the game does on its own
what the Lua edition does through hooks:

| asset | change |
|---|---|
| `BP_DIS` | the `ReceiveTick` event thunk enters the ubergraph at `CompleteCurrentPrompt`'s offset (two bytes of `.uexp`) |
| `WBP_DIS_Prompt_New` | class-default `Visibility` set to `Collapsed` |

`ReceiveTick` is the target because the engine calls it through `ProcessEvent`,
and BP_DIS only ticks while a prompt is running. `StartCurrentPrompt` cannot be
used: a Blueprint calling its own event bypasses the thunk. Both edits are
needed, since completing a prompt does not take its widget down.

`tools/pak/build_pak.py` extracts the two assets with retoc, proves a lossless
round-trip, applies both edits by name, verifies that the only changed bytes
are the offset literal, and repacks to an IoStore container. Nothing is
hardcoded, so a game patch that recompiles `BP_DIS` needs a rebuild rather
than a new analysis. The AES key is passed per build and never stored; the
mappings file lives in the gitignored `tools/bin/`. The container installs in
`Content\Paks` itself. Details, prerequisites and the inspection modes of the
patcher are in `tools/pak/README.md`.

The pak edition is versioned separately from the Lua mod. It has no toggle,
blocklist, ini or log, and it does not touch combat.

## Building the archives

```
python tools/build.py                    # dist/AutoQTE-<version>.zip; refuses debug flags left on
python tools/pak/build_pak.py --game …   # the pak container; see tools/pak/README.md
python tools/pak/build_archive.py        # dist/AutoQTE-PAK-<version>.zip
```

## Credits and licence

UE4SS was used for data collection and the development of AutoQTE, and no part of
UE4SS is bundled. Released under the MIT Licence, see `LICENSE.txt`. The Blood of
Dawnwalker is © Rebel Wolves; this mod is unofficial and ships no game assets.
