FROM mcr.microsoft.com/dotnet/sdk:9.0.318-bookworm-slim AS parser
WORKDIR /build
COPY companion/parser/PokeApp.Parser ./PokeApp.Parser
COPY companion/parser/PokeApp.Parser.Checks ./PokeApp.Parser.Checks
COPY deploy/parser-linux-x64.lock.json /build/parser-linux-x64.lock.json
RUN DOTNET_ROLL_FORWARD=Major dotnet run --project PokeApp.Parser.Checks -- --gen7 /fixtures
RUN DOTNET_ROLL_FORWARD=Major dotnet run --project PokeApp.Parser.Checks -- --progression /fixtures/progression
RUN dotnet publish PokeApp.Parser/PokeApp.Parser.csproj -c Release -r linux-x64 \
    --self-contained true -p:RuntimeFrameworkVersion=8.0.29 -p:RestoreLockedMode=true \
    -p:NuGetLockFilePath=/build/parser-linux-x64.lock.json -o /parser

FROM python:3.14.3-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
ENV POKEAPP_SERVER_PARSER=/opt/pokeapp-parser/PokeApp.Parser
WORKDIR /srv/pokeapp
COPY deploy/requirements-api.txt ./requirements-api.txt
RUN pip install --disable-pip-version-check -r requirements-api.txt \
    && apt-get update && apt-get install -y --no-install-recommends libicu72 libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home pokeapp
COPY --from=parser /parser /opt/pokeapp-parser
COPY --from=parser --chown=10001:10001 /fixtures /tmp/parser-fixtures
COPY app ./app
USER 10001
RUN python -c "import json,subprocess; r=subprocess.run(['/opt/pokeapp-parser/PokeApp.Parser'],input=b'',capture_output=True,check=True); assert json.loads(r.stdout)['error']=='TRUNCATED_SAVE'"
RUN python - <<'PY'
import json, pathlib, shutil, subprocess
root = pathlib.Path('/tmp/parser-fixtures')
for game, family in (('X', 'xy'), ('Y', 'xy'), ('OR', 'oras'), ('AS', 'oras'),
                     ('SN', 'sm'), ('MN', 'sm'), ('US', 'usum'), ('UM', 'usum')):
    result = subprocess.run(['/opt/pokeapp-parser/PokeApp.Parser'],
                            input=(root/family/game/'main').read_bytes(), capture_output=True, check=True)
    parsed = json.loads(result.stdout)
    assert parsed['error'] is None and parsed['observation']['game'] == game
    observed = parsed['observation']
    gen6 = family in ('xy', 'oras')
    assert len(observed['boxes']) == (31 if gen6 else 32)
    assert observed['progress'] is None
    native = observed['native_progress']
    assert native['schema_version'] == 1 and native['league_access'] is None
    assert native['model'] == ('gym_badges' if gen6 else 'island_challenge')
    assert native['badge_flags'] == ([False] * 8 if gen6 else None)
    assert native['island_stamp_flags'] == (None if gen6 else [False] * 4)
    assert native['champion_defeated'] is False
    result = subprocess.run(['/opt/pokeapp-parser/PokeApp.Parser'],
                            input=(root/'progression'/f'{game}-progress.main').read_bytes(),
                            capture_output=True, check=True)
    progressed = json.loads(result.stdout)
    assert progressed['error'] is None and progressed['observation']['progress'] is None
    native = progressed['observation']['native_progress']
    assert native['champion_defeated'] is gen6 and native['league_access'] is None
    assert native['badge_flags'] == ([False] * 8 if gen6 else None)
shutil.rmtree(root)
print('PASS Linux production-runtime eight-game parser and native progression smoke')
PY
CMD ["python", "-m", "app.api.serve"]
