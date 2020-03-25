#!/bin/bash

if [ "$(docker ps -aq -f name=nanome-postgnome)" != "" ]; then
    echo "removing exited container"
    docker rm -f nanome-postgnome
fi

HOST=`ipconfig getifaddr en0`

docker run -d \
--name nanome-postgnome \
--restart unless-stopped \
-e ARGS="$*" \
-e HOSTNAME=$HOST \
-v postgnome-volume:/root \
nanome-postgnome
