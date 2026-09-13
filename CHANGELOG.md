## 1.0.8

Changed
- The prompt is hidden by setting the widget's `Visibility` to `Collapsed`
  instead of writing `RenderOpacity = 0`. Same result on screen; it is the same
  property the .pak edition defaults in the asset, and it no longer contends
  with HUD mods that fade widgets by opacity.
- The diagnose key moves from F5 to INS. The mod's key check only sees other
  UE4SS mods, and a UE4SS key fires alongside a game binding; F5 is the game's
  quicksave, so every diagnose also quicksaved. Set `DiagnoseKey = F5` to keep
  the old key.

Hardening, each with a regression test and a mutation anchor
- Every `SetVisibility` is read back. A call that returns but does nothing no
  longer drops a widget still owed a restore. A read-back that is unreadable,
  or not a number, is treated as no evidence rather than as a failed write.
- F4 reports why it cannot enable the mod when the DIS hooks failed to
  register, instead of announcing `ENABLED`.
- Hook callbacks run under `xpcall`. An error is logged with its traceback and
  contained; the scene is kept and the mod stays on.
- A scene-start notification whose context cannot be read releases the
  tracked scene.
- A second playback-start for the same actor no longer announces `skipped:`
  twice, and the log-file write is guarded like every other I/O call.

Documentation
- `AutoQTE.defaults.ini` notes that several `BlockAlso` lines accumulate while
  a single value must not wrap.
- `BLOCKABLE-SCENES.md` lists all 59 blockable scenes, derived from the game's
  containers by asset class, and shows what the reference set covers.

Suite 65 -> 92 assertions, mutation battery 25 -> 35, 0 survivors.

## .pak edition 1.0.1

A second edition that needs no UE4SS, versioned separately from the Lua mod.
It overrides two cooked assets: `BP_DIS` has its `ReceiveTick` event pointed
at the ubergraph entry of `CompleteCurrentPrompt` (two bytes of `.uexp`), and
`WBP_DIS_Prompt_New` has its default `Visibility` set to `Collapsed`. Both
are needed: completing a prompt does not take its widget down.

No toggle key, no diagnose key, no blocklist, no ini, no log. It does not
touch combat.

1.0.1 is the container as `tools/pak/build_pak.py` reproduces it; the
payload is byte-identical to 1.0.0, whose package headers came from an
intermediate build the pipeline no longer produces. The build derives both
bytecode offsets by name, so a game patch that recompiles `BP_DIS` needs a
rebuild rather than a new analysis; it never echoes the AES key, refuses to
run over a non-stock container, and verifies that the only bytes changed are
the offset literal itself. See `tools/pak/README.md`.

## .pak edition 1.0.0

Initial release. Superseded by 1.0.1 (identical payload).

## 1.0.7

Fixed, from an external review of 1.0.5 whose five findings all reproduced.

- A completion that returned without throwing was taken as success. `call()`
  returns `(pcall ok, result)` and only the first was read, so an engine function
  that returns and does nothing was reported as a skip while the prompt stayed
  live under a hidden widget - the opposite of failing closed. The prompt state
  is now re-checked afterwards and handed back if it is still pending.
- A scene whose class we do not recognise returned before the supersede check,
  leaving the previous scene tracked; a later trigger could then complete a
  prompt in a scene that had already finished. Superseding now happens first.
- `hidePrompt` overwrote the latch of a widget whose restore had been refused,
  stranding it at our own 0.0 with nothing remembering it - the session-long
  invisible prompt that the retention exists to prevent. It now declines to hide
  a different widget while a restore is owed.
- An ini that opened but would not read was silently skipped, which looks
  identical to having no ini at all while the user's settings quietly do not
  apply. It now says so.
- `FindAllOf` was in the mandatory-globals gate but is used only by the F5
  sweep, so a build missing just that function disabled the whole mod. F5 now
  degrades on its own.

Suite 54 -> 65 assertions, battery 22 -> 25 mutants, 0 survivors; each fix has
a test that fails without it.

## 1.0.6

Added
- A disclaimer and bug-reporting section, in the shipped `README.txt` as well as
  on the mod page. It says plainly what the mod can and cannot take back: a
  completed scene is indistinguishable from one you completed by hand, but the
  mod removes the choice *not* to press, quest logic can tell a completed scene
  from a cancelled one, and a few director graphs do more than hand out a
  prompt. Save often, keep more than one save.
- Reporting guidance: press F5 during the scene, set `Verbose = true` first so
  the lines reach `AutoQTE.log`, and keep a save from just before if you can.

No code changes; `Scripts/main.lua` differs from 1.0.5 only in the version
string.

## 1.0.5

Changed
- The archive now carries the full path from the game folder
  (`Dawnwalker/Binaries/Win64/ue4ss/Mods/AutoQTE/`) instead of a `Data/` prefix.
  Extract it into the game folder and it merges into place; a mod manager
  deploying relative to the game root lands the same files in the same spots.
  The `Data/` prefix was a mod-manager-only convention that left manual
  installers digging a folder deeper than every other Dawnwalker Lua mod's
  instructions told them to.
- `README.txt` and `LICENSE.txt` moved inside the mod folder, so extracting no
  longer drops loose files in the game directory and deleting the mod folder
  removes its documentation with it.

Verified by extracting into a game folder holding another mod and a `mods.txt`:
AutoQTE lands correctly and neither is touched.

## 1.0.4

Minor documentation adjustments. No code changes: `Scripts/main.lua` is
identical to 1.0.3 apart from the version string.

- The shipped `README.txt` lists Steam build `25232147` among the verified
  builds; the 1.0.3 archive named only the two that preceded the 12 September
  patch.
- Mod-manager instructions are gone from the repo and from the shipped
  `README.txt`. They live on the Nexus page, which is where mod-manager users
  arrive from; a reader of the archive has already obtained it some other way.
- `README.md` links the Nexus page, points at the Releases page for downloads,
  and shows the `git clone` route for working on the mod.
- `tools/check_conflict.py` gates its keybind scan on documentation files, so a
  mod whose README merely quotes AutoQTE's own keys no longer raises a note
  against itself. A real `ToggleKey = F4` line in an ini is still caught.

## 1.0.3

Documentation and release tooling on top of 1.0.2. No behaviour changes: the
mod's code is identical apart from the version string and one comment.

Added
- `NEXUS.md`, the mod-page description, and `media/` for the page image.
- A note in `main.lua` recording why blood drinking is not automated. The hold
  duration is the story choice - it sets `KilledInnocentFactTag`, reaches
  `DrinkBloodSubsystem:OnInnocentKill` and is read by quest conditions - and
  three separate levers were measured and rejected: `bButtonPressed` is never
  read, driving `TickDrinking` advances the stage machine while the game sees no
  input, and `InputDrinkBlood` is edge-triggered, so a second press aborts the
  feed. It is written down so nobody retries it blind.

## 1.0.2

Fixed
- `BlockAlso` no longer fails open on the quoted form the README documents.
  `BlockAlso = "a", "b"` had the whole value unquoted before it was split on
  commas, producing the patterns `a"` and `"b` - which match nothing - while
  the mod still logged "2 blocklist patterns". The items are now unquoted
  individually, so a scene the user explicitly protected is actually protected.
- An inline-comment strip no longer truncates a value at a bare `;` or `#`.
  `BlockAlso = alpha#beta` became the pattern `alpha`, a *broader* substring
  that blocked scenes the user never named, and every pattern after the marker
  was dropped silently. A comment is now only recognised after whitespace.
- `(previous line xN)` reaches `AutoQTE.log` again; 1.0.1 emitted it through a
  bare `print` that never touched the log file.
- The ini parser no longer backtracks quadratically on a long whitespace run.

Tooling and documentation
- `tools/build.py` refused to ship only on the literal `true`; it now parses the
  value the way the mod does and catches `1`, `yes`, `on`, `"true"` and `DIS.`
  forms - all of which the 1.0.1 parser accepts.
- `README.md` shipped a headerless table fragment that GitHub rendered as a run
  of pipe characters in the Keybinds section.
- The documented key name `INSERT` is not a name UE4SS knows; it is `INS`.
- `README.txt` now carries the Xbox / Game Pass `Binaries\WinGDK` path.

# Changelog

Notable changes to AutoQTE. Versions follow SemVer.

## [1.0.1] — 2026-09-10

A correctness and documentation release. No change to what the mod does in a
normal scene; several changes to what it does when something goes wrong, and a
number of documented instructions that did not work.

### Fixed

- **A refused prompt-restore no longer hides the DIS prompt for the whole
  session.** If `SetRenderOpacity` was refused once when a scene ended, AutoQTE
  forgot the widget anyway, then read back its own `0.0` on the next scene and
  latched that as the "original" — leaving the prompt invisible from then on,
  with no way to recover in game. It now keeps the widget and retries.
- **A refused restore combined with a widget swap no longer writes the old
  widget's opacity onto the new one.**
- **The `BlockAlso` example in `AutoQTE.defaults.ini` was wrapped over four
  lines.** The parser reads one key per line, so uncommenting it applied only
  the first 4 of 13 patterns and reported success. It is now one line.
  **If you already copied that block into your own `AutoQTE.ini`, re-copy it
  from the new reference file** — your ini is never overwritten by an update, so
  this does not fix itself.
- **Settings the documentation recommended are no longer discarded in silence.**
  `DIS.HidePrompt = false` (the documented remedy for a HUD-mod interaction) and quoted key names such as `ToggleKey = "F4"` were both dropped
  without even a warning; the quoted form left the mod with no working keybinds.
  Both are now accepted, along with inline `;` comments and a UTF-8 BOM.
- **Any ini line that cannot be parsed is now counted** in the
  `N line(s) not understood` tally instead of vanishing.
- **A missing ini is now announced** rather than passing silently, which matters
  on install paths containing non-ASCII characters, where Lua cannot open the
  file at all.
- **The diagnose key now prints the scene identity** (`scene:`) that `BlockAlso`
  matches against. It previously printed only the actor name, which is a
  per-instance GUID and unusable as a pattern.
- **A log file that cannot be opened is no longer retried on every line**, and
  says so once.
- **The `(previous line xN)` repeat marker no longer strips the `[AutoQTE]` tag**
  off the message that follows it.

### Changed

- `tools/build.py` refuses to package debug flags left on in **either** shipped
  file — it previously checked only `main.lua`, missing `AutoQTE.defaults.ini`,
  which overrides it at runtime — and matches the parsed value, so `Verbose=true`
  is caught as well as `Verbose = true`. It also verifies the version in
  `main.lua` matches both READMEs, and names the archive `AutoQTE-<version>.zip`
  so a mod manager can read the version from it.
- `tools/check_conflict.py` no longer sets a verdict from a mod's documentation,
  detects ini-style keybinds (`toggleKey = F4`), reports the sequence-system,
  proxy-DLL and shared-library checks it already performed, and returns a shell
  exit code.

### Documentation

- Removed the note claiming settings live in `main.lua` and are destroyed by an
  update. They live in `AutoQTE.ini` and survive.
- Added an **Upgrading** section to both READMEs.
- Added the **Xbox / Game Pass** path: `Binaries\WinGDK`, not `Binaries\Win64`.
- Corrected the justification for shipping an empty blocklist. It previously
  claimed nothing downstream can branch on a prompt, that every director graph
  only calls `TriggerDISInteraction`, and that auto-completion costs you the
  chance to walk away. All three are false. What is true: AutoQTE can only ever
  produce the `Completed` end state, identical to completing the prompt by hand.
- Removed a duplicated settings table and a section documenting a Lua-only
  `BlockedScenes` list that ships empty.
- Verified builds are now CL-256181 and CL-258042.
- Documented that a single failed hook disables the mod entirely.

### Tests

- Suite 38 → **51 assertions**; mutation battery 13 → **20 mutants, 0 survivors**.
- Added coverage for the cancel hook, the diagnose key, the refused-restore
  recovery path, and every ini shape above — none of which were exercised before.
- Fixed a leak where one section's `AutoQTE.ini` fixture stayed set for the
  fifteen assertions that followed.
- `tests/mutants.py` now prunes stale mutants instead of leaving files behind
  that make the suite report a phantom failure.

## [1.0.0] — 2026-09-10

First public release.
