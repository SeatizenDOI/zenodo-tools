# Use an official Python runtime as a parent image
FROM python:3.11.9-slim

# Add local directory and change permission.
COPY . /app

# Setup workdir in directory.
WORKDIR /app

# Install lib.
RUN apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-mod-spatialite && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir \
    natsort==8.4.0 \
    pandas==2.2.2 \
    pycountry==24.6.1 \
    requests==2.32.3 \
    tqdm==4.66.4 \
    shapely==2.0.5 \
    scipy==1.14.0 \
    geopandas==1.0.1 \
    pyyaml==6.0.1 \
    suds==1.1.2 \
    dash==2.17.1 \
    dash_bootstrap_components==1.6.0 \
    dash_leaflet==1.0.15 \
    psutil==6.0.0 \
    gunicorn==22.0.0 \
    dash_extensions==1.0.18 \
    polars==1.3.0

EXPOSE 8050

# Define the entrypoint script to be executed.
ENTRYPOINT ["gunicorn", "--preload", "--workers", "4", "--threads", "4", "-t", "1000", "-b", "0.0.0.0:8050", "zenodo-monitoring:app"] 