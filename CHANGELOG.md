## 1.0.4

Minor documentation adjustments. No code changes: `Scripts/main.lua` is
identical to 1.0.3 apart from the version string.

- The shipped `README.txt` lists Steam build 25232147 among the verified builds;
  the 1.0.3 archive named only the two builds that preceded the 12 September
  patch.
- `README.md` links the Nexus page.

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
  `DIS.HidePrompt = false` (the documented remedy for the HUDTweaks
  interaction) and quoted key names such as `ToggleKey = "F4"` were both dropped
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
  so Vortex can read the version from it.
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
