from src.distance_calculate import process_region_grouped_distance, write__dist_geotiff
from src.tile_rasterize import generate_mask_tiles
from src.utils.helpers import MASK_DIR, DISTANCE_DIR
from pathlib import Path


if __name__ == "__main__":
    va_bbox = (-77.5, 37.2, -76.8, 37.8)

    common_config = {
        "pixel_size_deg": 0.0002,
        "tile_px": 512,
        "overlap_px": 16,
        "db_config": {
            "host": "localhost",
            "port": 5440,
            "dbname": "gis",
            "user": "postgres",
            "password": "postgres",
        },
    }

    # 1. GENERATE MASKS (Requires DB)
    print("--- Phase 1: Masking ---")
    generate_mask_tiles(va_bbox, output_dir=MASK_DIR, **common_config)
    # 2. COMPUTE DISTANCE (Uses Disk, DB is Fallback)
    distance_config = {
        **common_config,
        "block_tiles": 2,
        "halo_tiles": 1,
        "mask_input_dir": MASK_DIR,
    }
    print("\n--- Phase 2: Distance Calculation ---")
    for result in process_region_grouped_distance(va_bbox, **distance_config):
        r0, c0 = result["tile_row0"], result["tile_col0"]
        res_suffix = "res_0002"
        region = "USA_VA"
        filename = f"dist_{region}_{r0}_{c0}_{res_suffix}.tif"
        filepath = DISTANCE_DIR / filename
        write__dist_geotiff(
            path=filepath, arr=result["tile_dist"], bbox=result["tile_bbox"]
        )
        print(f"Saved Distance Tile: {r0}_{c0}")
