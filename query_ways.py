import psycopg
from shapely import wkb
import shapely
from typing import List

OSM_HIGHWAYS = [
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
]


def fetch_highways(
    bbox_tile,
    host="localhost",
    port=5440,
    dbname="gis",
    user="postgres",
    password="postgres",
    highway_filters=OSM_HIGHWAYS,
) -> List[shapely.geometry.LineString]:

    left, bottom, right, top = bbox_tile

    QUERY = """
    WITH bbox AS (
    SELECT ST_MakeEnvelope(%s, %s, %s, %s, 4326) AS geom
    )
    SELECT
    ST_AsBinary(l.way) AS geom_wkb,
    l.highway
    FROM public.planet_osm_line AS l, bbox AS b
    WHERE l.highway = ANY(%s)
    AND l.way && b.geom
    AND ST_Intersects(l.way, b.geom);
    """

    conn = psycopg.connect(
        host=host, port=port, dbname=dbname, user=user, password=password
    )
    try:
        with conn.cursor() as cur:
            # note param order matches the query (bbox coords first, then highway_filters)
            cur.execute(QUERY, (left, bottom, right, top, highway_filters))
            rows = cur.fetchall()
    finally:
        conn.close()
    out = []
    for geom_wkb, hw_tag in rows:
        g = wkb.loads(geom_wkb)
        if g is None or g.is_empty:
            continue
        out.append((g, hw_tag))
    return out


# to activate psql again: psql -h localhost -p 5440 -U postgres -d gis
