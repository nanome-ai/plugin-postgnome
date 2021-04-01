#!/bin/bash

docker cp ./settings.json postgnome:/root/Documents/nanome-plugins/postgnome/settings.json

docker exec postgnome chown root /root/Documents/nanome-plugins/postgnome/settings.json
docker exec postgnome chgrp nogroup /root/Documents/nanome-plugins/postgnome/settings.json
docker restart -t0 postgnome
