FROM --platform=linux/amd64 python:3.10-slim

# Set pip to have no saved cache
ENV PIP_NO_CACHE_DIR=false \
    POETRY_VIRTUALENVS_CREATE=false

ENTRYPOINT ["bash", "-c"]
CMD ["./entrypoint.sh"]

WORKDIR /bot

RUN pip install -U poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev

ARG git_sha="development"
ENV GIT_SHA=$git_sha

COPY . .
