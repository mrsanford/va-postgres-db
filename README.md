# Welcome to VA Postgres DB Repo

Welcome to the PostGIS/OSM repo, which tracks the changes for the containerized workflow and Python (uv-managed) section. This project allows users to start up the container, download data into a postgres database, immediately query, and ultimately get a distance-to-roads raster.

Things to figure out: 
- Allowing multiple repeat queries
- When creating a buffer, will need to account for this during the query portion
    - You could get the bounding box and then a function to go back and get a bounding box (like an extra *n* miles larger than the bbox, a box within a box and get the extras)
- File organization (Path)
- Figure out the projection and measuring units
- Generalize better for changes to non-hardcoded state or different part of the world (consult previous project)
- Add custom logging for Python-side or master logging or something like that
- Add tqdm? 

docker compose up -d
docker compose down
