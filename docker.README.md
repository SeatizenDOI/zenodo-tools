# Docker cheasheet

Automated build with github CI.

## Build

```bash
docker build -t zenodo-monitoring:latest . && \
docker tag zenodo-monitoring:latest seatizendoi/zenodo-monitoring:latest && \
docker push seatizendoi/zenodo-monitoring:latest
```

## Run


Bind a volume to avoid download the geopackage file.

```bash
docker run --rm -v ./seatizen_atlas_folder/:/app/seatizen_atlas_folder -p 8050:8050 seatizendoi/zenodo-monitoring:latest
```

```bash
docker run -d -p 8053:8050 seatizendoi/zenodo-monitoring:latest --name zenodo-monitoring
```