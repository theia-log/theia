FROM python:3.6.5-slim

COPY theia /theia
COPY requirements.txt /requirements.txt

RUN pip --no-cache-dir install -r /requirements.txt

RUN mkdir /data

ENV THEIA_PORT=6433
ENV THEIA_DATA_DIR=/data

EXPOSE 6433

ENTRYPOINT python -m theia.cli -P "${THEIA_PORT}" -H 0.0.0.0 collect -d "${THEIA_DATA_DIR}"

