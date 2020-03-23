#!/bin/bash

if [ "$(docker ps -aq -f name=nanome-postnome)" != "" ]; then
    echo "removing exited container"
    docker rm -f nanome-postnome
fi

HOST=`ipconfig getifaddr en0`

docker run -d \
--name nanome-postnome \
--restart unless-stopped \
-e ARGS="$*" \
-e HOSTNAME=$HOST \
-v postnome-volume:/root \
nanome-postnome
