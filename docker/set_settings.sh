#!/bin/bash

docker cp ./settings.json nanome-postgnome:/root/Documents/nanome-plugins/postgnome/settings.json

# docker exec nanome-postgnome chgrp --help
docker exec nanome-postgnome chown root /root/Documents/nanome-plugins/postgnome/settings.json
docker exec nanome-postgnome chgrp nogroup /root/Documents/nanome-plugins/postgnome/settings.json
docker restart -t0 nanome-postgnome