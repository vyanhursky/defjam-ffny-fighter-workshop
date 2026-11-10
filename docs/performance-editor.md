# Fighter performance authoring

This development feature extends roadmap fighter modpack authoring. It requires
the matching CAF v6 runtime source checkout and the player's supported game data.
It is not in the Beta 1 download. Story-save editing retains its existing scope.

Open a standalone project, then **Voice → Connect fighter runtime tools** and
select the companion source checkout. The connection is local to this editor
session; it is never stored in or executed from a fighter project. Original
catalogs and audition audio are read from the player's game files offline.

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

The **Animation** tab stages entrance and victory sequences independently of the
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

Project v7 stores shared performance separately from outfit appearance. Undo,
Reset, Save and Save As include these settings and original WAV bytes. Preview
snapshots expose clip duration/hash metadata rather than copying embedded audio
into the page state. Export writes ordinary typed voice, AI and cinematic
resources through the companion compiler; the whole package is validated before
publishing the ZIP. No Story progression, currency or machine paths are included.

CAF v6 and new identity binding tables distinguish fighters by stable roster
identity and participant. Two CAFs sharing a retail motion core can therefore
have different voices, AI and sequences. Old project/runtime formats retain their
existing meaning. The feature requires the matching runtime; full in-game and
cross-platform qualification is pending the owner's joint test session.
