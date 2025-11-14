import psycopg
from shapely import wkb

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
    host="localhost",
    port=5440,
    dbname="gis",
    user="postgres",
    password="postgres",
    highway_filters=OSM_HIGHWAYS,
):
    hw_values = ", ".join(f"'{hw}'" for hw in highway_filters)
    QUERY = f"""
    SELECT ST_AsBinary(way), highway
    FROM planet_osm_line
    WHERE highway IN ({hw_values});
    """
    conn = psycopg.connect(
        host=host, port=port, dbname=dbname, user=user, password=password
    )
    with conn.cursor() as cur:
        cur.execute(QUERY)
        rows = cur.fetchall()
    conn.close()

    geoms = []
    for geom_wkb, hw_tag in rows:
        geom = wkb.loads(geom_wkb)
        geoms.append((geom, hw_tag))
    return geoms
