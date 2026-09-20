# Minimal image for FritzDect2MQTT.
# Code + dependencies are baked in at build time; secrets.yaml is NOT included
# (it must never be committed) and is provided via a read-only bind mount at runtime.
#
# Build context = repository root (see docker/compose.yaml -> build.context: ..).

# Pinned to the 3.14 minor; rebuilds pick up the latest patch automatically.
FROM python:3.14-slim

WORKDIR /opt/fritzdect2mqtt

# Dependencies first for layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code + non-secret runtime config.
COPY FritzDect2MQTT.py MQTT.py configdata.cfg ./

# Run as an unprivileged user. The mounted secrets.yaml must be readable by
# UID 1000 (chown 1000:1000 + chmod 400 on the host). A home directory is
# needed: fritzconnection caches the router API description in ~/.fritzconnection.
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin app
USER app

ENV PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2 \
    MALLOC_TRIM_THRESHOLD_=100000 \
    FD2M_HEARTBEAT_FILE=/tmp/fritzdect2mqtt.alive

# Healthy = a full query cycle succeeded within the last 180 s (6 cycles at the
# default looptime of 30 s). Raise the limit if you use a much larger looptime.
HEALTHCHECK --interval=60s --timeout=5s --start-period=90s --retries=1 \
    CMD python -c "import os,sys,time; sys.exit(0 if time.time()-os.path.getmtime(os.environ['FD2M_HEARTBEAT_FILE'])<180 else 1)"

CMD ["python", "FritzDect2MQTT.py"]
