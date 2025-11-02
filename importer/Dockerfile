FROM debian:stable

RUN apt-get update && apt-get install -y \
        wget osm2pgsql postgresql-client && \
        rm -rf /var/lib/apt/lists/*

WORKDIR /data

COPY import.sh /import.sh
RUN chmod +x /import.sh

ENTRYPOINT ["/import.sh"]