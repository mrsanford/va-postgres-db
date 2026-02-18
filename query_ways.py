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
    """
    bbox_tile is in EPSG:4326 (left, bottom, right, top) = (lon_min, lat_min, lon_max, lat_max)
    planet_osm_line.way is in EPSG:3857 (osm2pgsql default)
    Returns geometries transformed back to EPSG:4326 for tile compatibility.
    """
    left, bottom, right, top = bbox_tile

    QUERY = """
    WITH bbox AS (
    SELECT ST_Transform(
            ST_MakeEnvelope(%s, %s, %s, %s, 4326),
            3857
            ) AS geom_3857
    )
    SELECT ST_AsBinary(ST_Transform(way, 4326)) AS geom_wkb, highway
    FROM planet_osm_line, bbox
    WHERE highway = ANY(%s)
    AND way && bbox.geom_3857
    AND ST_Intersects(way, bbox.geom_3857);
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
    return [(wkb.loads(geom_wkb), hw_tag) for geom_wkb, hw_tag in rows]
