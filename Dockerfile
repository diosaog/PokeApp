FROM mcr.microsoft.com/dotnet/sdk:9.0.318-bookworm-slim AS parser
WORKDIR /build
COPY companion/parser/PokeApp.Parser ./PokeApp.Parser
COPY deploy/parser-linux-x64.lock.json /build/parser-linux-x64.lock.json
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
COPY app ./app
USER 10001
RUN python -c "import json,subprocess; r=subprocess.run(['/opt/pokeapp-parser/PokeApp.Parser'],input=b'',capture_output=True,check=True); assert json.loads(r.stdout)['error']=='TRUNCATED_SAVE'"
CMD ["python", "-m", "app.api.serve"]
