# Docker cheasheet

## Build

```bash
docker build -t zenodo-monitoring-image:latest . && \
docker tag zenodo-monitoring-image:latest groderg/zenodo-monitoring-image:latest && \
docker push groderg/zenodo-monitoring-image:latest
```

## Run
docker run --rm -v /home/bioeos/Documents/project_hub/zenodo-tools/seatizen_atlas_folder/:/app/seatizen_atlas_folder -p 8050:8050 zenodo-monitoring-image:latest
