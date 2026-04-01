from distance_calculate import process_region_grouped_distance, write__dist_geotiff
from tile_rasterize import generate_mask_tiles
import os

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
    mask_dir = "./va_tiles/mask"
    os.makedirs(mask_dir, exist_ok=True)
    print("--- Phase 1: Masking ---")
    generate_mask_tiles(va_bbox, output_dir=mask_dir, **common_config)
    # 2. COMPUTE DISTANCE (Uses Disk, DB is Fallback)
    dist_dir = "./va_tiles/distance"
    os.makedirs(dist_dir, exist_ok=True)
    distance_config = {
        **common_config,
        "block_tiles": 2,
        "halo_tiles": 1,
        "mask_input_dir": mask_dir,
    }
    print("\n--- Phase 2: Distance Calculation ---")
    for result in process_region_grouped_distance(va_bbox, **distance_config):
        r0, c0 = result["tile_row0"], result["tile_col0"]
        filepath = os.path.join(dist_dir, f"dist_USA_VA_{r0}_{c0}.tif")
        write__dist_geotiff(
            path=filepath, arr=result["tile_dist"], bbox=result["tile_bbox"]
        )
        print(f"Saved Distance Tile: {r0}_{c0}")
