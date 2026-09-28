FROM python:3.14.3-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv/pokeapp
COPY deploy/requirements-api.txt ./requirements-api.txt
RUN pip install --disable-pip-version-check -r requirements-api.txt \
    && useradd --uid 10001 --create-home pokeapp
COPY app ./app
USER 10001
CMD ["python", "-m", "app.api.serve"]
