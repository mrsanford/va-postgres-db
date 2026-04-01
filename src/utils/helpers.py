from pathlib import Path

_SELF_DIR = Path(__file__).resolve().parent
ROOT_DIR = _SELF_DIR.parent

DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "rasters"
RAW_DIR = DATA_DIR / "raw"

# -- TIFF Specifics ---
MASK_DIR = OUTPUT_DIR / "mask"
DISTANCE_DIR = OUTPUT_DIR / "distance"

for folder in [DATA_DIR, OUTPUT_DIR, RAW_DIR, MASK_DIR, DISTANCE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

CRS = "EPSG:4326"
LON_MIN, LON_MAX = -180.0, 180.0
LAT_MIN, LAT_MAX = -90.0, 90.0
