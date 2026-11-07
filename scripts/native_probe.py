"""Run an explicitly selected game executable against private copied data.

No global process termination, no original-save writes and no runtime patches.
Call with --source-data, --exe, --output (a new directory), --profile and --seconds.
Only the selected profile and title metadata are copied; game assets are linked
read-only by convention and the writable save root belongs to this run.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from defjam_caf.profiles import discover
from defjam_caf.fields import apply_fields


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-data", type=Path, required=True)
    ap.add_argument("--exe", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--profile", default="VY3")
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--stage", action="append", default=[])
    ap.add_argument("--edit-json", type=Path)
    ap.add_argument("--inject")
    args = ap.parse_args()
    source = args.source_data.resolve()
    out = args.output.resolve()
    if out.exists() or out == source or source in out.parents:
        raise SystemExit("Output must be a new independent directory outside source data")
    discovered = discover(source)
    selected = next(p for p in discovered.profiles if p.name == args.profile)
    original = manifest(source / "save" / "UserData")
    out.mkdir(parents=True)
    title = out / "data" / "save" / "UserData" / "45410049"
    shutil.copytree(selected.path.parent, title / selected.path.parent.name)
    # Exercise the actual codec (and optional field editor), not just a file copy.
    edits = json.loads(args.edit_json.read_text()) if args.edit_json else {}
    encoded = apply_fields(selected.container, edits).encode()
    (title / selected.path.parent.name / selected.name).write_bytes(encoded)
    (out / "source-manifest-before.json").write_text(json.dumps(original, indent=2))
    for p in discovered.title_root.iterdir():
        if p.is_file():
            shutil.copy2(p, title / p.name)
    # Windows junctions need no symbolic-link privilege.
    if os.name == "nt":
        link_env = dict(os.environ, CAF_PROBE_LINK=str(out / "game"),
                        CAF_PROBE_TARGET=str(source / "extracted"))
        result = subprocess.run(["powershell", "-NoProfile", "-Command",
                                 "New-Item -ItemType Junction -Path $env:CAF_PROBE_LINK -Target $env:CAF_PROBE_TARGET | Out-Null"],
                                env=link_env, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace"))
    else:
        (out / "game").symlink_to(source / "extracted", target_is_directory=True)
    shutil.copy2(args.exe, out / args.exe.name)
    for dll in args.exe.parent.glob("*.dll"):
        shutil.copy2(dll, out / dll.name)
    stages = [("getscreeninfo(intmain/mainmenu", "a:6:6.3"),
              ("getscreeninfo(options/userid", "down:4:4.3,a:9:9.3,a:15:15.3,a:22:22.3,a:29:29.3"),
              ("getscreeninfo(story/crib", "down:4:4.3,a:6:6.3")]
    for stage in args.stage:
        anchor, presses = stage.split("=", 1)
        stages = [(a, p) for a, p in stages if a != anchor] + [(anchor, presses)]
    pads = ["start:14:14.3", "start:17:17.3"] + [f"a:{n}:{n}.3" for n in range(20, 90, 3)]
    for anchor, presses in stages:
        pads.extend(["@" + anchor, presses])
    env = {k: v for k, v in os.environ.items() if not k.startswith("RECOMP_")}
    env.update(DEFJAM_DATA=str(out / "data"), RECOMP_SETTINGS="none", RECOMP_VBLANK="1",
               RECOMP_PB_EXEC="1", RECOMP_PB_D3D11="1", RECOMP_USB="1", RECOMP_SKIP_INTRO="1",
               RECOMP_UNLOCK_ALL="0", RECOMP_ASPECT="4:3", RECOMP_CRYPTO_TRACE="1",
               RECOMP_SCRIPT_ANCHOR="getscreeninfo(intmain/prestart", RECOMP_PAD_SCRIPT=",".join(pads),
               RECOMP_TRANS_SHOT=str(out / "native.bmp"),
               RECOMP_TRANS_SHOT_SECS="@getscreeninfo(options/userid,16,28,@controller.getcontrollersenabled#14,3,8,15,@getscreeninfo(story/crib,10,30,41,51,61")
    if args.inject:
        env["RECOMP_FE_INJECT"] = args.inject
    before = manifest(out / "data" / "save" / "UserData")
    with (out / "stdout.log").open("wb") as stdout, (out / "stderr.log").open("wb") as stderr:
        child = subprocess.Popen([str(out / args.exe.name)], cwd=out, env=env, stdout=stdout, stderr=stderr)
        print(json.dumps({"pid": child.pid, "executable": str(out / args.exe.name), "output": str(out)}), flush=True)
        started = time.monotonic()
        samples = []
        next_sample = 40
        while child.poll() is None and time.monotonic() - started < args.seconds:
            time.sleep(.5)
            elapsed = time.monotonic() - started
            if elapsed >= next_sample:
                next_sample += 30
                try:
                    from read_native_profile import scan
                    records = scan(child.pid, out / args.exe.name, out / "stderr.log", selected.name)
                    samples.append(dict(seconds=round(elapsed, 1), records=records))
                    (out / "resident-profiles.json").write_text(json.dumps(samples, indent=2))
                except Exception as exc:
                    samples.append(dict(seconds=round(elapsed, 1), error=str(exc)))
        controlled_stop = child.poll() is None
        if controlled_stop:
            # Only the Popen object created above may be stopped.
            child.terminate()
            child.wait(timeout=15)
    original_after = manifest(source / "save" / "UserData")
    unchanged = original == original_after
    changed = [p for p in original.keys() | original_after.keys() if original.get(p) != original_after.get(p)]
    from defjam_caf.profiles import directory_name
    option_dirs = {directory_name("Options"), directory_name("Options", legacy=True)}
    profiles_unchanged = not any(not (len(Path(p).parts) > 1 and Path(p).parts[1] in option_dirs) for p in changed)
    text = (out / "stderr.log").read_text(errors="replace")
    report = {"source_userdata_unchanged": unchanged, "exit_code": child.returncode,
              "controlled_stop": controlled_stop, "reached_crib": "Control.GetScreenInfo(story/crib" in text,
              "crash_marker": any(marker in text for marker in ("[CRASH]", "Failed to resolve", "[FATAL]")),
              "source_profile_sha256": selected.sha256, "source_profiles_unchanged": profiles_unchanged,
              "source_changed_files": changed, "edits": edits,
              "codec_unchanged": encoded == selected.container.encode(), "before": before,
              "after": manifest(out / "data" / "save" / "UserData"),
              "exe_sha256": hashlib.sha256((out / args.exe.name).read_bytes()).hexdigest()}
    (out / "receipt.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"source_unchanged": unchanged, "profiles_unchanged": profiles_unchanged,
                      "exit_code": child.returncode}), flush=True)
    if not profiles_unchanged:
        raise SystemExit("Original fighter profiles changed during the probe; inspect concurrent game activity")


if __name__ == "__main__":
    main()
