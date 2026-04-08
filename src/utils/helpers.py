from pathlib import Path

_SELF_DIR = Path(__file__).resolve().parent
ROOT_DIR = _SELF_DIR.parent.parent

DATA_DIR = ROOT_DIR / "data"

# -- TIFF Specifics ---
OUTPUT_DIR = ROOT_DIR / "visualization"
MASK_DIR = OUTPUT_DIR / "mask"
DISTANCE_DIR = OUTPUT_DIR / "distance"

for folder in [DATA_DIR, OUTPUT_DIR, MASK_DIR, DISTANCE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

CRS = "EPSG:4326"
LON_MIN, LON_MAX = -180.0, 180.0
LAT_MIN, LAT_MAX = -90.0, 90.0
RES_SUFFIX = "res_0002"
REGION = "USA_VA"

# Be able to adjust the tile size (level 8 tiles vs level 6 tiles) and not just the pixel size
# Mess with halo adjuster (at 1 tile right now, allow fractional tiles)

# Test Case Example
# 80% halo tile overhang on level 4

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
