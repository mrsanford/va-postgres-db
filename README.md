# Welcome to VA Postgres DB Repo

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

