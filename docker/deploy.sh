#!/bin/bash

echo "./deploy.sh $*" > redeploy.sh
chmod +x redeploy.sh

existing=$(docker ps -aq -f name=postgnome)
if [ -n "$existing" ]; then
    echo "removing existing container"
    docker rm -f $existing
fi

HOST=`ipconfig getifaddr en0`

docker run -d \
--name postgnome \
--restart unless-stopped \
-e ARGS="$*" \
-e HOSTNAME=$HOST \
-v postgnome-volume:/root \
postgnome
