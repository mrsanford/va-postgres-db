import psycopg
from shapely import wkb
from typing import List, Tuple
from shapely.geometry import base
from src.utils.helpers import OSM_HIGHWAYS, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS


def fetch_highways(
    bbox_tile: Tuple[float, float, float, float],
) -> List[Tuple[base.BaseGeometry, str]]:
    """
    Fetches highways from PostGIS using credentials defined in environment variables.
    """
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
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                QUERY, (left, bottom, right, top, OSM_HIGHWAYS)
            )  # passing OSM_HIGHWAYS to the query
            rows = cur.fetchall()
    finally:
        conn.close()
    out = []
    for geom_wkb, hw_tag in rows:
        try:
            g = wkb.loads(bytes(geom_wkb))
            if g is None or g.is_empty:
                continue
            out.append((g, hw_tag))
        except Exception:
            continue
    return out
