import psycopg
from shapely import wkb
from typing import List, Tuple
from shapely.geometry import base
from src.utils.helpers import OSM_HIGHWAYS


def fetch_highways(
    bbox_tile,
    host="localhost",
    port=5440,
    dbname="gis",
    user="postgres",
    password="postgres",
    highway_filters=OSM_HIGHWAYS,
) -> List[Tuple[base.BaseGeometry, str]]:
    left, bottom, right, top = bbox_tile
    QUERY = """
    WITH bbox AS (
        SELECT ST_MakeEnvelope(%s, %s, %s, %s, 4326) AS geom
    )
    SELECT
        ST_AsBinary(l.way) AS geom_wkb,
        l.highway
    FROM public.planet_osm_line AS l, bbox AS b
    WHERE l.highway = ANY(%s::text[])
      AND l.way && b.geom
      AND ST_Intersects(l.way, b.geom);
    """
    conn = psycopg.connect(
        host=host, port=port, dbname=dbname, user=user, password=password
    )
    try:
        with conn.cursor() as cur:
            # Total 5 arguments: 4 for envelope, 1 for highway list
            cur.execute(QUERY, (left, bottom, right, top, highway_filters))
            rows = cur.fetchall()
    finally:
        conn.close()
    out = []
    for geom_wkb, hw_tag in rows:
        try:
            g = wkb.loads(geom_wkb)
            if g is None or g.is_empty:
                continue
            out.append((g, hw_tag))
        except Exception:
            continue
    return out
