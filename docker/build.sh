#!/bin/bash

if [[ $(docker volume ls -f name=postgnome-volume -q) ]]; then
    echo "Skipping volume creation"
else
    echo "Creating new docker volume"
    docker volume create postgnome-volume
fi

cachebust=0
while [ $# -gt 0 ]; do
  case $1 in
    -u | --update ) cachebust=1 ;;
  esac
  shift
done

if [ ! -f ".cachebust" ] || (($cachebust)); then
  date +%s > .cachebust
fi

cachebust=`cat .cachebust`
docker build -f Dockerfile --build-arg CACHEBUST=$cachebust -t nanome-postgnome:latest ..
