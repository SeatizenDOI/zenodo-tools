#!/bin/bash

# First, we delete the current zenodo manager image
docker image rm seatizendoi/zenodo-manager:latest

docker run --user 1000 --rm \
  -v /home/debian/villien/zenodo-tools-config/config.json:/home/seatizen/app/config.json \
 --name zenodo-manager seatizendoi/zenodo-manager:latest python zenodo-auto-update.py


# All code to restart the zenodo-monitoring container.
docker container stop zenodo-monitoring 

docker image rm seatizendoi/zenodo-monitoring:latest

docker run -d --rm --name zenodo-monitoring -p 8053:8050 seatizendoi/zenodo-monitoring:latest