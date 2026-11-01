FROM mcr.microsoft.com/dotnet/sdk:9.0.318-bookworm-slim AS parser
WORKDIR /build
COPY companion/parser/PokeApp.Parser ./PokeApp.Parser
COPY companion/parser/PokeApp.Parser.Checks ./PokeApp.Parser.Checks
COPY deploy/parser-linux-x64.lock.json /build/parser-linux-x64.lock.json
RUN DOTNET_ROLL_FORWARD=Major dotnet run --project PokeApp.Parser.Checks -- --gen7 /fixtures
RUN DOTNET_ROLL_FORWARD=Major dotnet run --project PokeApp.Parser.Checks -- --progression /fixtures/progression
RUN DOTNET_ROLL_FORWARD=Major dotnet run --project PokeApp.Parser.Checks -- --training-runtime-fixtures /fixtures /fixtures/training
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
import json, pathlib, subprocess
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
print('PASS Linux production-runtime eight-game parser and native progression smoke')
PY
RUN python - <<'PY'
import hashlib, json, pathlib, shutil
from app.save_parser.write_models import WriteIntent
from app.save_parser.writer import PkhexProcessWriter

root = pathlib.Path('/tmp/parser-fixtures')
training = root / 'training'
manifest = json.loads((training / 'cases.json').read_text())
assert manifest['schema_version'] == 1 and len(manifest['cases']) == 24
writer = PkhexProcessWriter(pathlib.Path('/opt/pokeapp-parser/PokeApp.Parser'))
seen = set()
for case in manifest['cases']:
    game, item = case['game'], case['item_code']
    assert game in ('X', 'Y', 'OR', 'AS', 'SN', 'MN', 'US', 'UM')
    assert item in ('menta_naturaleza', 'chapa_plateada', 'chapa_dorada')
    assert (game, item) not in seen and case['source_file'] == f'{game}/main'
    seen.add((game, item))
    source_path = training / case['source_file']
    source = source_path.read_bytes()
    intent = WriteIntent.create(**case['intent'])
    mutation, expected = intent.mutation, case['expected']
    assert intent.game == game and mutation['item_code'] == item
    assert expected['nature'] == (15 if item == 'menta_naturaleza' else 3)
    assert expected['ivs'] == ([3, 5, 7, 9, 11, 13] if item == 'menta_naturaleza' else
                               [31, 5, 7, 9, 11, 13] if item == 'chapa_plateada' else [31] * 6)
    assert hashlib.sha256(source).hexdigest() == intent.expected_sha256
    before = writer.inspect_training(source, mutation['location'], mutation['box_index'], mutation['slot_index'])
    assert before['nature'] == 3 and before['ivs'] == [3, 5, 7, 9, 11, 13]
    prepared = writer.prepare(source, intent)
    # prepare already verifies; repeat against a separate immutable copy as
    # server-side persisted-output verification does in the production image.
    output = bytes(bytearray(prepared.output))
    writer.verify(source, output, intent, prepared)
    after = writer.inspect_training(output, mutation['location'], mutation['box_index'], mutation['slot_index'])
    assert after['nature'] == expected['nature'] and after['ivs'] == expected['ivs']
    # Expected hash was computed from an independently edited synthetic PKM,
    # with zero HT flags. Equality covers every stored byte, including flags.
    assert expected['no_hyper_training'] is True
    assert after['pokemon_sha256'] == expected['pokemon_sha256']
    assert after['target_pid'] == before['target_pid'] and after['target_ec'] == before['target_ec']
    assert source_path.read_bytes() == source and output != source and len(output) == len(source)
    diff = prepared.semantic_diff
    assert all(diff[k] is True for k in ('preserved_unrelated', 'checksums_valid', 'signature_valid'))
    print(f'PASS Linux production-runtime virtual training {game} {item}')
assert len(seen) == 24
shutil.rmtree(root)
print('PASS Linux production-runtime 24 virtual training cases; actual Nature/IV, exact PKM, native output verification, no HT flags')
PY
CMD ["python", "-m", "app.api.serve"]
