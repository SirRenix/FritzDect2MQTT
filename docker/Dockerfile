# Minimal image for FritzDect2MQTT.
# Code + dependencies are baked in at build time; secrets.yaml is NOT included
# (it must never be committed) and is provided via a read-only bind mount at runtime.
#
# Build context = repository root (see docker/compose.yaml -> build.context: ..).

FROM python:3.14.2-slim

WORKDIR /opt/fritzdect2mqtt

# Dependencies first for layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code + non-secret runtime config.
COPY FritzDect2MQTT.py MQTT.py configdata.cfg ./

ENV PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2 \
    MALLOC_TRIM_THRESHOLD_=100000

CMD ["python", "FritzDect2MQTT.py"]
