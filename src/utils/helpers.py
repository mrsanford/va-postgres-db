from pathlib import Path
import os

# --- Core Pathing ---
_SELF_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = _SELF_DIR.parent.parent
ROOT_DIR = Path(os.getenv("ROOT_DIR", DEFAULT_ROOT))

# --- Directory Constants ---
OUTPUT_DIR = ROOT_DIR / os.getenv("OUTPUT_DIR_NAME", "visualization")
PIPELINE_DIR = ROOT_DIR / os.getenv("PIPELINE_DIR_NAME", "pipeline")
MASK_DIR = OUTPUT_DIR / os.getenv("MASK_DIR_NAME", "mask")
DISTANCE_DIR = OUTPUT_DIR / os.getenv("DISTANCE_DIR_NAME", "distance")

for folder in [OUTPUT_DIR, PIPELINE_DIR, MASK_DIR, DISTANCE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

CRS = os.getenv("CRS", "EPSG:4326")
REGION = os.getenv("REGION", "USA_VA")

LON_MIN = float(os.getenv("LON_MIN", -180.0))
LON_MAX = float(os.getenv("LON_MAX", 180.0))
LAT_MIN = float(os.getenv("LAT_MIN", -90.0))
LAT_MAX = float(os.getenv("LAT_MAX", 90.0))

_DEFAULT_HIGHWAYS = "motorway,motorway_link,trunk,trunk_link,primary,primary_link,secondary,secondary_link,tertiary,tertiary_link"
OSM_HIGHWAYS = os.getenv("OSM_HIGHWAYS", _DEFAULT_HIGHWAYS).split(",")

PIXEL_SIZE_DEG = float(os.getenv("PIXEL_SIZE_DEG", 0.0001))
RES_SUFFIX = os.getenv(
    "RES_SUFFIX", "res_0001"
)  # For naming purposes, it's best to make sure RES_SUFFIX and PIXEL_SIZE_DEG are the same
TILE_PX = int(os.getenv("TILE_PX", 1024))
OVERLAP_PX = int(os.getenv("OVERLAP_PX", 0))
BLOCK_TILES = int(os.getenv("BLOCK_TILES", 4))
HALO_TILES = float(os.getenv("HALO_TILES", 0.8))

# # --- Tile & Halo Settings (Addressing your TODOs) ---
# # Level 8 default, but now adjustable via ENV
# TILE_LEVEL = int(os.getenv("TILE_LEVEL", 8))
# # Halo as a fraction (e.g., 0.8 for 80% overhang)
# HALO_SIZE = float(os.getenv("HALO_SIZE", 1.0))
