# Docker cheasheet

## Build

```bash
docker build -t zenodo-monitoring-image:latest . && \
docker tag zenodo-monitoring-image:latest groderg/zenodo-monitoring-image:latest && \
docker push groderg/zenodo-monitoring-image:latest
```

## Run


Bind a volume to avoid download the geopackage file.

```bash
docker run --rm -v /home/bioeos/Documents/project_hub/zenodo-tools/seatizen_atlas_folder/:/app/seatizen_atlas_folder -p 8050:8050 groderg/zenodo-monitoring-image:latest
```

```bash
docker run --rm -p 8053:8050 groderg/zenodo-monitoring-image:latest
```