# Fighter performance authoring

Performance tools belong to standalone fighter projects and require a compatible
game version selected in **Game setup**, plus the player's supported game data.
They ship in Workshop Beta 2; current source connects catalogs automatically.
Story-save editing retains its existing scope.

The same panels/settings apply to standalone fighters started from CAF or retail
donors. Retail appearance replacements/extra outfits retain their parent's shared
performance. Retail source animation preview requires the optional
`retail-animation-preview-1` runtime extension (companion runtime PR269, v1.2.0).
Without it, voice/AI/presentation authoring and export still use the existing API;
only unsupported preview controls are disabled. With it, the shared player supports
entrance/victory, source clips, play/pause, scrubbing and stop on the selected body.

Open a standalone project and visit **Voice**, **Entrance & victory**, or **AI**.
The first visit loads the selected game's catalogs. Inline errors offer Retry;
Voice also offers **Reload voice & animation catalogs**. Game setup remembers
the selected runtime outside the project; it is never executed from a project.
Original
catalogs and audition audio are read from the player's game files offline.

**Stage voice settings** also prepares the selected fighter's voices in the
background. A progress count appears under the player; editing remains available.
Choose a clip to play it, or use **Previous clip** / **Next clip**. Turn off
**Play when selecting a clip** to browse silently. **Audition imported** compares
an imported override with the original. WAVs are cached privately with size
limits and do not get embedded in the project merely because you audition them.

**Save WAV…**, or the player's **Download** menu, opens a save dialog. After
saving, Workshop displays the full path and offers **Open folder**. Cancelling
the dialog writes nothing. This exports only the loaded audition; it does not
export the fighter's whole voice bank or modify the game files.

## Voice

Choose an independent retail voice preset, optionally override Character,
Taunts or Enviro banks, then Stage voice settings. Bank clip slots use original
event ordinals; unverified semantics are not assigned invented names. Audition
an original or imported clip, import mono PCM16 WAV (8–48 kHz, at most 8 MiB per
clip), or explicitly clear an override. Embedded audio has a 64 MiB total budget.
Changing the preset retains existing overrides and refuses incompatible slots.

Entrance/victory speech have separate override slots. Original audition uses
the first available stream. A preset without clip edits keeps the native retail
voice route; an edited bank exports that first original entrance/victory stream
as its default unless replaced. It does not preserve every randomized stream.

## Entrance, victory and playback

The **Entrance & victory** tab stages entrance and victory sequences independently of the
motion core. Inherit restores the presentation donor for that role. Original
sequences retain their native camera and secondary resources in the game export.

The viewer plays supported original body/root curves using physical skeleton
rows and the model's actual palette weights. Play/pause, timeline scrubbing,
looping and speed are preview-only. Stop restores the selected static pose.
Changing the fighter/outfit or refreshing its scene cancels playback. Skinning
does not bake the current pose into sculpts or projects.

Browse original retail or CAF animation banks by source token. Preflight excludes
unsupported codecs. The first decoder supports body types 18/13 and root type 20;
type 19 and other unsupported body codecs are currently excluded. For example,
the verified Blaze bank has 7 supported clips and 110 exclusions. Playback uses
30 source ticks per second, without claiming exact native timing. Camera motion,
face/hand palette animation, event dispatch and runtime blending are not shown.
This is source-track playback, separate from the approximate static pose menu.

## AI

Choose an original AI profile and edit 23 named tendencies across easy, normal
and hard difficulty, with four original slots each. Check a field to override
it with 1–5; unchecked fields retain exact original values, including values
outside that authoring range. Slots retain their native selection rules. They
are not named phases, and a larger value is not universally more aggressive.
Stage AI personality applies all edited difficulties/slots. Changing the preset
resets unstaged slider edits; Inherit removes the project AI override.

## Persistence and export

Projects store shared performance separately from outfit appearance. Undo,
Reset, Save and Save As include these settings and original WAV bytes. Preview
snapshots expose clip duration/hash metadata rather than copying embedded audio
into the page state. Export writes ordinary typed voice, AI and cinematic
resources through the companion compiler; the whole package is validated before
publishing the ZIP. No Story progression, currency or machine paths are included.

The matching runtime's identity binding tables distinguish fighters by stable roster
identity and participant. Two CAFs sharing a retail motion core can therefore
have different voices, AI and sequences. Old project/runtime formats retain their
existing meaning. The feature requires the matching runtime; full in-game and
cross-platform qualification is pending the owner's joint test session.


## Authored CAF victory lip sync

A paired Blender bridge can retain bounded Blaze `CE_113A` facial mouth tracks
in `performance.cinematics.victory`. Victory uses the imported **extro** WAV;
entrance keeps its separate **intro** WAV and authored tracks. Save/reopen and
export preserve both. Changing a donor or voice without matching mouth timing
is refused. Export requires the runtime extension `caf-victory-mouth-1`.

Edit Jaw Open and Lip Shape in the prepared Blender scene, use its voice
waveform/word markers and 50% sound-plus-animation preview, then export a new
performance document and matching WAV. The paired converter validates these
closed controls and merges only victory settings into a new project/package.
The regular Workshop source-animation preview still omits facial evaluation.
An exported document or Blender playback does not establish native acceptance.
