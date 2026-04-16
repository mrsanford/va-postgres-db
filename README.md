# Geofabrik-OSM Raster Pipeline

This project encompasses a customized, containerized workflow for ingesting OpenStreetMap (OSM) data into PostGIS and generating high-resolution "distance-to-roads" raster.

## Quick Start

1. **Initialize the Environment**
The project uses `docker compose` to orchestrate the PostGIS database and the Python processing environments. 
``` 
# To start the stack
docker compose up

# Stop the stack
docker compose down
```

2. **Access the Database**
After the container starts and is running, you can connect to the local PostGIS instance:
```
psql - h localhost -p 5440 -U postgres -d gis
```

## Raster Generation
**Distance Seam Mitigation**
**Configuration Goals**


## Init
```docker compose up```
The first time will start the container, download the data into a PostGRES/PostGIS database, and allow queries. 
```docker compose down```

Welcome to the PostGIS/OSM repo, which tracks the changes for the containerized workflow and Python (uv-managed) section. This project allows users to start up the container, download data into a postgres database, immediately query, and ultimately get a distance-to-roads raster.

Buffer boxes:
1. You could get the bounding box and then a function to go back and get a bounding box (like an extra *n* kms larger than the bbox, a box within a box and get the extras)
2. **Make buffer configurable 1km^2 pixel or 3-5km^2s**
3. Pixel size & determining a max distance cap
    - Play with small chunks of Virginia (10kms around with buffer)
    - Fix the database
    - Update the querying logic

Chunk the raster. Determine the size of the total raster.
The buffer created of the subsetted raster, extend those bounds and calculate everything inside the bounds.
Two bounding boxes, extend of the actual sub raster, second bounding box is the bounds + the buffer (THIS BUFFER SHOULD BE CONFIGURABLE)
- Might need to convert units
- You should be able to query the database with the raster bounding boxes

Quick Aside:
- PostGIS spatially indexes the data by location
- The database can handle data inside bounding boxes

docker compose up -d
docker compose down

The goal is one massive raster for the world
1. Prebuild the raster plan
2. Calculate the entire size of the world raster depending on the pixel size

Decide how big the raster will be!!!!! Size the pixels based on?
Standard mercator projection is degrees and convert it to get it to ~1km^2 in VA

Test this hands on
- pick a subset
- add bounding box and visualize
- so you can see on QGIS the subset and bounding box (so just a box)

Next week: plan to come up with visualization
Structure out steps and determine
- Pick a subset of around Richmond and the bounding box of like 5-10 miles

accessing psql
psql -h localhost -p 5440 -U postgres -d gis

calculate the tile extent and the encompassing bounding
fixed number of extra degrees in any direction 
ENCOMPASSING_BOUNDING_BOX_PERCENT


What packages and what scripts for the container?
Add container to do the compiling work

FROM ghcr.io/astral-sh/uv:debian

# Dependency Install

build container for packaging python
UV Documentation -- There is a container with UV
add uv dependencies to dockerfile

DOCKER:
COPY just the pyproject.toml
COPY just the .python-version
COPY the uv.lock
uv sync

COPY src

# github actions right after the docker
# everytime you commit, container will be rebuilt