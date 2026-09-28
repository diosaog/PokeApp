"""Export only committed API deployment inputs; never upload the working directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.exists():
        raise SystemExit('Output must be a new directory.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit], cwd=root, text=True).splitlines()
    allowed = [n for n in names if n.startswith('app/') and n.endswith('.py')]
    allowed += ['Dockerfile', '.dockerignore', 'deploy/requirements-api.txt']
    for name in allowed:
        if name not in names:
            raise SystemExit('Missing committed deployment input: '+name)
    output.mkdir(parents=True)
    hashes = {}
    for name in allowed:
        raw = subprocess.check_output(['git', 'show', commit+':'+name], cwd=root)
        dest = output/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    (output/'deployment-source.json').write_text(json.dumps({'commit': commit, 'sha256': hashes}, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'commit': commit, 'files': len(allowed), 'output': str(output)}))


if __name__ == '__main__':
    main()
