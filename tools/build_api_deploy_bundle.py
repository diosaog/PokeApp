"""Export only committed API deployment inputs; never upload the working directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


WORKER = """USER root
COPY deploy/requirements-item-verifier.txt /tmp/requirements-item-verifier.txt
RUN pip install --disable-pip-version-check -r /tmp/requirements-item-verifier.txt
COPY deploy/certs /srv/pokeapp/deploy/certs
COPY tools/run_item_use_verifier.py /srv/pokeapp/run_item_use_verifier.py
USER 10001
ENV POKEAPP_NATIVE_PARSER_PATH=/opt/pokeapp-parser/PokeApp.Parser
CMD ["sh", "-c", "while true; do python run_item_use_verifier.py; sleep 5; done"]
"""


def worker_dockerfile(api):
    """The API image, ending in the verifier loop instead of the web server."""
    head, sep, _ = api.rpartition('CMD ["python", "-m", "app.api.serve"]')
    if not sep:
        raise SystemExit('Unexpected API Dockerfile: no API CMD to replace.')
    return head + WORKER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    # The hosted verifier: the same image plus psycopg, the Supabase CA and a 5 s loop.
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.exists():
        raise SystemExit('Output must be a new directory.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit], cwd=root, text=True).splitlines()
    allowed = [n for n in names if n.startswith('app/') and n.endswith('.py')]
    allowed += [n for n in names if n.startswith(('companion/parser/PokeApp.Parser/', 'companion/parser/PokeApp.Parser.Checks/'))
                and (n.endswith(('.cs', '.csproj')) or n.endswith('/packages.lock.json'))]
    allowed += ['Dockerfile', '.dockerignore', 'deploy/requirements-api.txt', 'deploy/parser-linux-x64.lock.json']
    if args.worker:
        allowed += ['tools/run_item_use_verifier.py', 'deploy/requirements-item-verifier.txt',
                    'deploy/certs/supabase-prod-ca-2021.crt']
    for name in allowed:
        if name not in names:
            raise SystemExit('Missing committed deployment input: '+name)
    output.mkdir(parents=True)
    hashes = {}
    for name in allowed:
        raw = subprocess.check_output(['git', 'show', commit+':'+name], cwd=root)
        if args.worker and name == 'Dockerfile':
            raw = worker_dockerfile(raw.decode()).encode()
        dest = output/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    (output/'deployment-source.json').write_text(json.dumps({'commit': commit, 'sha256': hashes}, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'commit': commit, 'files': len(allowed), 'output': str(output)}))


if __name__ == '__main__':
    main()
