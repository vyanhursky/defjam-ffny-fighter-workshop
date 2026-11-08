"""Verify and relocate a native package, then check its frozen offline UI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

NAME = 'defjam-ffny-fighter-workshop'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New private receipt/workspace directory')
    args = parser.parse_args()
    archive = args.archive.resolve()
    expected = Path(str(archive) + '.sha256').read_text(encoding='utf-8').split()[0]
    digest = hashlib.sha256()
    with archive.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise SystemExit('Package checksum mismatch')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    # Spaces and non-ASCII exercise file URLs, framework links and relocation.
    with tempfile.TemporaryDirectory(prefix='workshop relocated ü ') as temporary:
        relocated = Path(temporary)
        if sys.platform == 'darwin':
            subprocess.run(['ditto', '-x', '-k', str(archive), str(relocated)], check=True)
            app = relocated / (NAME + '.app')
            subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
            executable = app / 'Contents' / 'MacOS' / NAME
        elif sys.platform == 'linux':
            with tarfile.open(archive) as bundle:
                bundle.extractall(relocated, filter='data')
            executable = relocated / NAME / NAME
        elif sys.platform == 'win32':
            shutil.unpack_archive(archive, relocated)
            executable = relocated / NAME / (NAME + '.exe')
        else:
            raise SystemExit('Unsupported native platform')
        env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'PYTHONHOME'}}
        receipt = output / 'startup.json'
        with (output / 'launcher.log').open('wb') as log:
            subprocess.run([str(executable), '--workspace', str(output / 'workspace'),
                            '--smoke-test', str(receipt)], cwd=relocated, env=env,
                           stdout=log, stderr=subprocess.STDOUT, timeout=150, check=True)
        result = json.loads(receipt.read_text(encoding='utf-8'))
        if not result.get('passed') or not result.get('frozen'):
            raise SystemExit('Frozen desktop startup failed: ' + str(result))
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
