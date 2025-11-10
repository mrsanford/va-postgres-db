import psycopg
from shapely import wkb

conn = psycopg.connect(
    host="localhost", port=5440, dbname="gis", user="postgres", password="postgres"
)

with conn.cursor() as cur:
    cur.execute("""
        [Add Query]
    """)
    rows = cur.fetchall()

geometries = []
for geom_wkb, hw in rows:
    geom = wkb.loads(geom_wkb)
    geometries.append((geom, hw))

print(type(geometries[0][0]), geometries[0][1])
