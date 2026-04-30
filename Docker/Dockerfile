# ---------- BUILD STAGE ----------
FROM python:3.13-slim-bookworm AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /MusicBot
COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- RUNTIME STAGE ----------
FROM python:3.13-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openjdk-21-jre-headless \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /MusicBot

COPY --from=builder /install /usr/local
COPY . .

RUN mkdir -p logs plugins && \
    groupadd -g 999 basicuser && useradd -r -u 999 -g basicuser basicuser && \
    chown -R basicuser:basicuser /MusicBot

USER basicuser

CMD ["bash", "startup.sh"]
