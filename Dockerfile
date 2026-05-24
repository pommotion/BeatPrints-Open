FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8010

WORKDIR /app

COPY pyproject.toml poetry.lock README.md LICENSE ./
COPY BeatPrints ./BeatPrints
COPY cli ./cli
COPY web ./web

RUN pip install --no-cache-dir .

EXPOSE 8010

CMD ["python", "-m", "web.app", "--host", "0.0.0.0"]
