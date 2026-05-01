# GeoFabrik-OSM Raster Pipeline

This project provides an automated pipeline for generating road network masks and calculating Euclidean distance rasters using OpenStreetMap (OSM) data. 

## Architecture
The system is divided into three functional portions:
### 1. PostGIS Database
A containerized Postgres/PostGIS instance that stores OSM data. The test case for this project is the US state of Virginia.
### 2. OSM Importer
An automated service that downloads and imports the latest .osm.pbf file into the database.
### 3. Workflow Runner
The Python-based processing engine handling the mask and distance calculations in tiled blocks.

## Getting Started
* Docker and Docker Compose
* Disk Space: Ensure 16GB available for OSM data processing (for Virginia)


## Quick Start

### 1. Pre-Built Image
If using the preconfigured workflow image, pull the image directly to your machine:
```docker pull ghcr.io/mrsanford/va-postgres-db:main```

### 2. Configuration
There are a handful of adjustable environment variables defined in `helpers.py` and the `docker-compose.yaml` file. Custom options can be overwritten in a `.env` file.
* `REGION`: The prefix name for your output files (default is `USA_VA`)
* `PIXEL_SIZE_DEG`: The resolution (e.g., `0.0001` corresponds to roughly 10m/pixel)
* `OSM_HIGHWAYS`: The road types to include in queries and calculations (default include primary, secondary, and tertiary motorways and trunks)

### 3. Running the Pipeline
Launch the stack with Docker Compose, which handles database setup, data import, and automated script execution.
```bash
docker compose up -d
```

## Technical File Reference
```.
├── .venv/
├── .github/
│   ├── utils/
│      └── build.yml
├── db/
│   ├── Dockerfile
│   └── init-db.sh
├── importer/
│    ├── Dockerfile
│    └── import.sh
├── osmdata/
│   ├── pgdata/
│       ├── *           # All PostGIS database infrastructure and content exists
├── src/
│   ├── utils/
│   │   └── helpers.py
│   ├── distance_calculate.py
│   ├── query_ways.py
│   └── tile_rasterize.py
├── vizualization/
│   ├── distance/
│   ├── mask/
├── compute.py
├── docker-compose.yaml
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

## Output References
The file `compute.py` controls the automation of the workflow execution and is managed through the `docker-compose.yml` but can also be managed by `uv run compute.py`. The pipeline populates the `visualization/` directory defined in `helpers.py`.

## Logic and Processing Deep Dive
The workflow has been engineered for a tiled, buffered approach to generating a global-scale raster plan while adhering to memory limits. It gracefully handles perceived mask "seams", which commonly arise in large spatial programming where comparing tiles does not return continuous rasters when mosaicked.

### 1. Global Grid Planning
The system calculates the dimensions of the "global raster" upfront based on the `PIXEL_SIZE_DEG`.
* Coordinate-to-Pixel Mapping: `tile_rasterize.py` maps geographic coordinates (in Lat/Lon) to a global pixel index.
* Pixel sizes are in standard Mercator degrees (EPSG:4326). Target resolution is variable and customizable (see environment variables).

### 2. Halo Strategy
The system mitigates distance inaccuracies at tile edges by employing a dual bounding box methodology.
* The Target Tile: The actual `n x n` pixel area (= 1 tile) that will be saved to disk. The size of the tiles are an environment variable and are configurable. The default is 512 x 512.
* The Encompassing Bounding Box (The Halo): the workflow offers a configurable parameter to extend the bounds of the sub-raster by the `HALO_TILES` multiplier. This constant takes fractional and whole integer values. The default is 0.8 of a tile, so the extent of the distance calculation will include the sub-raster + 80% halo.
* Seamless Gradients: Everything is calculated inside the expanded halo box + target raster before being clipped back to the target tile. The returned output is the Target Tile with edge pixels calculated to consider distance calculations in neigboring tiles. 


### 3. Database Querying
The `query_ways.py` script uses `psycopg` to handle PostGIS to Python querying. 
For efficient spatial indexing in target tiles and halo buffers:
* Spatial Intersects: Queries are bounded to the halo box dimensions. This is to avoid repeat query requests to the database for redundant or multiple queries.
* Tag Filtering: The query script is filtered to only return highway types defined in `OSM_HIGHWAYS` to reduce overhead in unecessary datum.

### 4. Raster Assembly and Distance Math
* Masking: Roads are masked with a binary 0/1 mask for road networks. 0 for no road and 1 for road.
* Euclidean Calculation: `distance_calculate.py` applies the `distancerasters` library to calculate the distance transform on the mask.
* Batch/Block Processing: the systemm groups tiles into `BLOCK_TILES` unit for batched distance calculations. 

The output from the distance raster calculations are individual distance GeoTIFFs.

### Visualizing in QGIS
The methodology was tested by subsetting 30km regions near Richmond and Chesapeake, VA, respectively.

## License and Credits
* Data Source: OpenStreetMap (OSM) via GeoFabrik

### Tips and Tricks
**Connecting to the Database**
`psql - h localhost -p 5440 -U postgres -d gis`