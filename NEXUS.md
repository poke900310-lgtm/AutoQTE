# AutoQTE

## Description

I made this mod because devs putting in unnecessary button prompts is the
continuing bane of my existence.

Dawnwalker puts a button prompt in front of a lot of small scenes. AutoQTE
presses it for you.

The scene is not skipped and nothing is faked. The mod calls the game's own
`CompleteCurrentPrompt` - the same function your keypress calls - so the scene
ends in the Completed state and every quest node downstream sees exactly what it
expects.

**What it deliberately leaves alone**

Combat, parries, finishers, hold-to-interact, and blood drinking. Voracious Bite
especially: how long you hold decides whether the victim lives or dies, that sets
a persistent fact tag, and quest conditions read it. That is a story choice, not
a chore, so the mod stays out of it.

Tested on The Blood of Dawnwalker, Steam, build 25232147 (the 12 September 2026
patch). All four hooks resolve and scenes auto-complete on that build.

## Installation instructions

**Vortex** - install the archive. It uses the "UE4SS (Lua mods)" layout and lands
in the right place on its own.

**Manual** - extract `Data\AutoQTE\` into your Mods folder:

```
Steam:      ...\The Blood of Dawnwalker\Dawnwalker\Binaries\Win64\ue4ss\Mods\
Game Pass:  ...\The Blood of Dawnwalker\Dawnwalker\Binaries\WinGDK\ue4ss\Mods\
```

You should end up with `Mods\AutoQTE\enabled.txt` and
`Mods\AutoQTE\Scripts\main.lua`. No `mods.txt` entry is needed - the mod loads
from its own `enabled.txt`.

**Configuration** - settings live in `AutoQTE.ini` beside `main.lua`. It is not
shipped: create it, and it will survive mod updates, unlike
`AutoQTE.defaults.ini`, which is the reference copy and gets overwritten.

```ini
Enabled = true
HidePrompt = true
ToggleKey = F4
DiagnoseKey = F5
BlockAlso =
Verbose = false
```

Key names are UE4SS names: `F4`, `INS`, `HOME`, `NUM_FIVE`. Leave a key empty to
not bind it. Settings load at startup, so restart the game after editing.

**Uninstallation** - delete the `AutoQTE` folder. Nothing else is touched.

## Main features

- Completes DIS (dialogue interaction scene) prompts automatically
- Hides the prompt ring while it works, and restores it afterwards
- **F4** toggles the mod on and off at any time, even mid-scene. Switch it off
  and the live prompt comes back for you to play
- **F5** writes the current scene's state to the log, for reporting a scene that
  misbehaves
- Optional blocklist if you would rather perform certain scenes yourself
- Empty blocklist by default - nothing is blocked until you say so

## Requirements

UE4SS. Any working install will do.

**Compatibility** - four native hooks and two keybinds. No `.pak`, no assets, no
`mods.txt` entry, and it does not touch `dwmapi.dll` or `UE4SS-settings.ini`, so
it will not fight your UE4SS install or any other package over those files.

It only conflicts with another mod that drives the same DIS prompts. HUD and UI
mods are fine; if one of them fades the prompt ring, set `HidePrompt = false`.

If F4 or F5 are already taken by another mod, AutoQTE says so in the log and does
not bind - change `ToggleKey` in the ini.

## Shout outs

UE4SS-RE and its contributors, none of this exists without the loader.

Vercadi, for maintaining the Dawnwalker UE4SS package.

Rebel Wolves, for a game whose scene system turned out to be clean enough to
hook safely.
