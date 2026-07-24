# ---------- BUILD STAGE ----------
FROM python:3.13-slim-trixie AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /MusicBot
COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- RUNTIME STAGE ----------
FROM python:3.13-slim-trixie

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openjdk-21-jre-headless \
        ca-certificates \
        curl \
        zip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /MusicBot

COPY --from=builder /install /usr/local
COPY . .

# Download the Lavalink server jar at build time so it never lives in git.
# Bump with: docker build --build-arg LAVALINK_VERSION=x.y.z ...
ARG LAVALINK_VERSION=4.2.2
RUN curl -fsSL -o Lavalink.jar \
        "https://github.com/lavalink-devs/Lavalink/releases/download/${LAVALINK_VERSION}/Lavalink.jar"

RUN mkdir -p logs plugins && \
    groupadd -g 999 basicuser && useradd -r -u 999 -g basicuser basicuser && \
    chown -R basicuser:basicuser /MusicBot

USER basicuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('localhost',2333)); s.close()"

CMD ["bash", "startup.sh"]
