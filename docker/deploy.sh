if [ "$(docker ps -aq -f name=nanome-postnome)" != "" ]; then
    # cleanup
    echo "removing exited container"
    docker rm -f nanome-postnome
fi

docker run -d \
--name nanome-postnome \
--restart unless-stopped \
-e ARGS="$*" \
nanome-postnome
