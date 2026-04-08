from src.distance_calculate import process_region_grouped_distance, write__dist_geotiff
from src.tile_rasterize import generate_mask_tiles
from src.utils.helpers import MASK_DIR, DISTANCE_DIR, REGION, RES_SUFFIX


if __name__ == "__main__":
    va_bbox = (-83.67, 36.54, -75.16, 39.46)
    # (-77.5, 37.2, -76.8, 37.8)
    common_config = {
        "pixel_size_deg": 0.0001,
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

    # update the level of the pixels -- not just how many pixels in each tile
    # but how many tiles

    # --- Masking ---
    generate_mask_tiles(va_bbox, output_dir=MASK_DIR, **common_config)

    # --- Distance Calculation ---
    distance_config = {
        **common_config,
        "block_tiles": 3,
        "halo_tiles": 1.4,
        "mask_input_dir": MASK_DIR,
    }
    for result in process_region_grouped_distance(va_bbox, **distance_config):
        r0, c0 = result["tile_row0"], result["tile_col0"]
        filename = f"dist_{REGION}_{r0}_{c0}_{RES_SUFFIX}.tif"
        filepath = DISTANCE_DIR / filename
        write__dist_geotiff(
            path=filepath, arr=result["tile_dist"], bbox=result["tile_bbox"]
        )
        print(f"Saved Distance Tile: {r0}_{c0}")
