FROM mcr.microsoft.com/dotnet/sdk:9.0.318-bookworm-slim AS parser
WORKDIR /build
COPY companion/parser/PokeApp.Parser ./PokeApp.Parser
COPY companion/parser/PokeApp.Parser.Checks ./PokeApp.Parser.Checks
COPY deploy/parser-linux-x64.lock.json /build/parser-linux-x64.lock.json
RUN DOTNET_ROLL_FORWARD=Major dotnet run --project PokeApp.Parser.Checks -- --gen7 /fixtures
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
COPY --from=parser --chown=10001:10001 /fixtures/sm /tmp/parser-sm-fixtures
COPY --from=parser --chown=10001:10001 /fixtures/usum /tmp/parser-usum-fixtures
COPY app ./app
USER 10001
RUN python -c "import json,subprocess; r=subprocess.run(['/opt/pokeapp-parser/PokeApp.Parser'],input=b'',capture_output=True,check=True); assert json.loads(r.stdout)['error']=='TRUNCATED_SAVE'"
RUN python - <<'PY'
import json, pathlib, shutil, subprocess
for game in ('SN', 'MN', 'US', 'UM'):
    root = pathlib.Path('/tmp/parser-sm-fixtures' if game in ('SN', 'MN') else '/tmp/parser-usum-fixtures')
    result = subprocess.run(['/opt/pokeapp-parser/PokeApp.Parser'],
                            input=(root/game/'main').read_bytes(), capture_output=True, check=True)
    parsed = json.loads(result.stdout)
    assert parsed['error'] is None and parsed['observation']['game'] == game
    assert len(parsed['observation']['boxes']) == 32
shutil.rmtree('/tmp/parser-sm-fixtures')
shutil.rmtree('/tmp/parser-usum-fixtures')
print('PASS Linux production-runtime Sun/Moon and Ultra Sun/Ultra Moon parser smoke')
PY
CMD ["python", "-m", "app.api.serve"]
