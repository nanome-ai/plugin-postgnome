if [[ $(docker volume ls -f name=postnome-volume -q) ]]; then
    echo "Skipping volume creation"
else
    echo "Creating new docker volume"
    docker volume create postnome-volume
fi

docker build -f Dockerfile -t nanome-postnome:latest ..