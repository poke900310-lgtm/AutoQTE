# Rebuilding the .pak edition

The pak edition needs no UE4SS at runtime. Building it does - once, to dump a
mappings file.

**A game patch that recompiles `BP_DIS` invalidates the shipped pak.** Rebuilding
is one command, because nothing here is hardcoded: the patcher reads the
bytecode offsets out of the asset by function name each run. That is the whole
reason it is a tool and not a recorded byte edit.

## What it changes

Two assets, two different kinds of edit:

| asset | change | size |
|---|---|---|
| `BP_DIS` | `ReceiveTick` -> `CompleteCurrentPrompt` | 2 bytes of `.uexp` |
| `WBP_DIS_Prompt_New` | `Visibility` -> `Collapsed` | one enum |

The first completes the prompt; the second stops it being drawn. **Both are
needed.** Completing a prompt does not take its widget down, so a build with
only the first auto-completes everything and leaves the prompt sitting on
screen - which is exactly how the first working build behaved.

### Why `ReceiveTick` and not `StartCurrentPrompt`

Every Blueprint event compiles to a thunk that enters the ubergraph:

```
[one EX_LetValueOnPersistentFrame per parameter]
ExecuteUbergraph_BP_DIS(<offset>) ; Return ; EndOfScript
```

`CompleteCurrentPrompt` is three instructions; `ReceiveTick(DeltaSeconds)` is
four, the extra one copying its parameter into the frame. The only thing
separating one event from another is that integer, so pointing one event's
offset at another's makes it run the other's graph. The patcher only trusts an
integer that is the argument of a call into `ExecuteUbergraph_*` - a function
with a body of its own also has calls with integer arguments, and those are
not entry offsets.

But a call from **inside the same Blueprint does not go through the thunk** -
the compiler emits a direct jump into the ubergraph instead. So redirecting a
thunk only affects callers *outside* the Blueprint. `StartCurrentPrompt` has
none: BP_DIS starts its own prompts internally. Redirecting it is inert, and
indistinguishable from the mod not loading at all.

`ReceiveTick` is the opposite case. It is the Blueprint Tick event, invoked
natively by the engine through `ProcessEvent` - always through the thunk. And
BP_DIS's class defaults carry `bStartWithTickEnabled = False`, so the actor only
ticks while a prompt is actually running. Redirecting Tick therefore means "the
moment a prompt starts driving this actor, finish it", and costs nothing the
rest of the time.

### Why the widget edit is data and not bytecode

`WBP_DIS_Prompt_New` imports no `SetVisibility`, no `SetRenderOpacity`, nothing
visibility-related at all - check with `--list-imports` if that ever changes. So
its graph never overwrites the default, and collapsing the default is enough.
CommonUI's activation path does not re-show it either (verified in game).

## One-time setup

1. **retoc** - <https://github.com/trumank/retoc>. Converts Zen (IoStore) to
   legacy assets and back. Not vendored here; put it on PATH or pass `--retoc`.
2. **.NET SDK** - to run `tools/pak/patcher`.
3. **The game's AES key.** The containers are encrypted. The key is
   deliberately **not** in this repository and should not be added to it:
   publishing a commercial game's decryption key is a different act from
   publishing a mod. Pass it per build, or set `AUTOQTE_AES_KEY`.
4. **A `.usmap`.** UE5 cooked assets store properties without names, so nothing
   can parse them without a mappings file. To dump one:
   - install UE4SS temporarily,
   - add a Lua mod that calls `DumpUSMAP()` on a keybind,
   - launch, press the key, and take the `.usmap` written beside `UE4SS.dll`,
   - remove UE4SS again.

   Re-dump after any game patch: the mappings describe that build.

   **Keep it in `tools/bin/`** (gitignored; the build looks there first). A
   mappings file that only lives beside `UE4SS.dll` is deleted along with it,
   and uninstalling UE4SS is the normal state once the pak edition is in use.

## Build

```
set AUTOQTE_AES_KEY=0x...
python tools/pak/build_pak.py --game "G:\Steam\steamapps\common\The Blood of Dawnwalker"
```

**Move any previously installed `AutoQTE_P.*` out of `Content\Paks` first.**
Extraction reads that directory the way the game does, mod containers included,
so building over an installed mod extracts the already-patched asset and the
patcher refuses it as "already patched". Rebuilding after a game update is
precisely when the old mod is still sitting there. The build checks for this by
name and stops with instructions.

Four stages, each gated on the one before:

1. **extract** both assets from the game's containers. Pass the `Paks`
   *directory*, not a single `.utoc` - retoc needs `global.utoc` alongside to
   resolve package names, and without it a name filter silently matches nothing
   and extracts zero files without failing.
2. **round-trip** each asset unchanged and require byte-identical output. If the
   library has stopped understanding some part of the asset, that shows up here
   rather than as a mod that loads and misbehaves. The build refuses to patch if
   this fails.
3. **patch**, then re-read the result and confirm the edit is really there. The
   bytecode edit also counts bytes differing from a clean re-serialisation of
   the stock asset and **refuses** anything outside the bound: `.uasset` must
   be untouched and `.uexp` may differ by 1-4 bytes (the offset is a
   little-endian int32; on this build it is 2). More than that means
   something other than the offset moved.
4. **repack** to IoStore and verify the container.

Output is `dist/AutoQTE_P.{utoc,ucas,pak}`. Install by copying all three into
`<game>\Dawnwalker\Content\Paks\`.

**`Content\Paks` itself, not a subfolder.** That is where the container was
verified to mount. The `~mods` subfolder was only ever tried with the inert
`StartCurrentPrompt` build, so nothing is known about it either way; use the
location that is proven.

## Inspecting the assets

The patcher doubles as a read-only inspector, which is how every decision above
was made:

```
dotnet run --project tools/pak/patcher -- <asset.uasset> <mappings.usmap> out.uasset --list-functions
```

`--list-functions` prints each event's ubergraph offset, `--list-defaults`
recurses into the class defaults, `--list-imports` shows what the asset
references. `--from`/`--to` select which pair of events to redirect;
`--set-enum=Name:Value` and `--set-double=Name:Value` edit class defaults.
`--enum <Name>` prints a usmap enum's values in index order (how `Collapsed = 1`
is shown), `--list-props` dumps every export's properties including data-table
rows. `--classify <dir>` prints every `.uasset` under a directory with its top-level
export classes; `tools/pak/list_dis_scenes.py` uses it to regenerate
`BLOCKABLE-SCENES.md` - the full list of DIS scenes, derived by asset class
rather than by folder or name, with the shipped `BlockAlso` reference set
cross-checked against it.

## Checking it actually works

The shipping build compiles logging out - `Saved\Logs` stays empty and
`LogBlueprintUserMessages` does not appear in the executable - so the pak
edition cannot report anything about itself. To watch it, install the UE4SS
edition alongside in observer mode:

```ini
Enabled = false
Verbose = true
LogEveryCompletion = true
```

`Enabled = false` stops it completing prompts while it still logs scene start
and end. Anything that auto-completes then was the pak, not the script. Without
that distinction you cannot tell which of the two did what.

Be careful reading the trigger count: a `trigger:` line is one prompt, not one
button press. Woodchopping is six prompts, and it logs six of them whether the
player pressed or the pak did. The log proves the scene completed; only the
player can say whether they pressed anything.

If a build ever appears to do nothing, the question to answer first is whether
the container mounted at all - a mount failure and an inert patch look identical
from in game. The cheapest test is a data-only container: change one class
default to a distinctive value and read it back from a UE4SS Lua mod with
`StaticFindObject("/Game/.../BP_DIS.Default__BP_DIS_C")`. Reading the live actor
as well separates "the asset edit did not apply" from "it applied and something
overrides it at runtime".

## What the pak edition cannot do

No F4 toggle, no F5 diagnose, no blocklist, no ini, no logging. All of that is
script behaviour with nowhere to live in an asset override. It is all-or-nothing
auto-complete, and that is the trade for not needing UE4SS.

It also does not touch combat. Voracious Bite and blood drinking run through
`DrinkBloodSubsystem`, not `BP_DIS`; this was confirmed in game.
