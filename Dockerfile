FROM alpine:latest

RUN apk --update add python3 && \
    rm -rf /var/cache/apk/*

COPY theia /theia
COPY requirements.txt /requirements.txt

RUN pip3 --no-cache-dir install -r /requirements.txt

RUN mkdir /data

ENV THEIA_PORT=6433
ENV THEIA_DATA_DIR=/data

EXPOSE 6433

CMD ["/bin/sh", "-c", "python3 -m theia.cli -P ${THEIA_PORT} -H '0.0.0.0' collect -d ${THEIA_DATA_DIR}"]

