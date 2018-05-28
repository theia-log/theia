FROM alpine:latest

RUN apk --update add python3 && \
    rm -rf /var/cache/apk/*

COPY theia /theia
COPY requirements.txt /requirements.txt
COPY docker/theia-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN pip3 --no-cache-dir install -r /requirements.txt

RUN mkdir /data

ENV THEIA_PORT=6433
ENV THEIA_DATA_DIR=/data
ENV THEIA_DATA_STORE=rdbs
ENV THEIA_DB_URL="sqlite:////data/events.db"

EXPOSE 6433

ENTRYPOINT "/entrypoint.sh"

