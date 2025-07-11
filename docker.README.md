# Docker cheasheet

Images are automatically built with a CI pipeline on github. They are available under the name :
* seatizendoi/zenodo-manager:latest
* seatizendoi/zenodo-monitoring:latest

If you want to run docker image from dockerhub add seatizendoi/ to the beginning of image name.

But you can build them yourself :

## zenodo-manager

The goal of this docker image is to be a ready-made environment to easily run scripts.

Build command :

```bash
docker build -f Dockerfile.manager -t zenodo-manager:latest .
```

Run command :
```bash
docker run --user 1000 --rm \
  -v ./seatizen_atlas_folder/:/home/seatizen/app/seatizen_atlas_folder \
  -v ./config.json:/home/seatizen/app/config.json \
 --name zenodo-manager zenodo-manager:latest python zenodo-auto-update.py
```

## zenodo-monitoring

This image docker is a dash server which allows you to view and interact with geopackage data.

Build command :
```bash
docker build -f Dockerfile.monitoring -t zenodo-monitoring:latest .
```

Run command
```bash
docker run --rm -v ./seatizen_atlas_folder/:/app/seatizen_atlas_folder --name zenodo-monitoring -p 8050:8050 seatizendoi/zenodo-monitoring:latest
```