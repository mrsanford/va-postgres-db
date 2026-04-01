import distancerasters as dr
import numpy as np
import rasterio
from pathlib import Path
from rasterio.transform import from_bounds
from src.utils.helpers import CRS, MASK_DIR, REGION, RES_SUFFIX
from typing import Tuple, Iterator
from src.tile_rasterize import (
    tile_iter_over_bbox,
    window_to_bbox,
    build_mask_tile,
    clip_array_to_window,
)


# --- Distance GeoTIFF ---
def write__dist_geotiff(
    path: Path | str, arr: np.ndarray, bbox: Tuple[float, float, float, float]
):
    """Writes a float32 distance raster to a GeoTIFF"""
    h, w = arr.shape
    transform = from_bounds(*bbox, w, h)
    profile = {
        "driver": "GTiff",
        "height": h,
        "width": w,
        "count": 1,
        "dtype": "float32",  # CRITICAL: Match the float32 array
        "crs": CRS,
        "transform": transform,
        "compress": "lzw",  # Better for float data
        "nodata": -9999,  # Standard for float rasters
    }
    with rasterio.open(path, "w", **profile) as dst:
        # Fill NaNs with your nodata value before writing
        write_arr = np.nan_to_num(arr, nan=-9999)
        dst.write(write_arr.astype(np.float32), 1)


# --- Calculate Distance ---
def calculate_distance(
    rv_array: np.ndarray, transform, output_path: Path | str | None = None
) -> np.ndarray:
    rv_array = rv_array.astype(np.uint8, copy=False)

    def raster_conditional(rarray: np.ndarray) -> np.ndarray:
        return rarray == 1

    dr_obj = dr.DistanceRaster(
        rv_array,
        affine=transform,
        conditional=raster_conditional,
        output_path=output_path,
    )
    return dr_obj.dist_array.astype(np.float32, copy=False)


# --- Full Distance Flow ---
def process_region_grouped_distance(
    global_bbox: Tuple[float, float, float, float],
    pixel_size_deg: float,
    tile_px: int,
    overlap_px: int,
    block_tiles: int,
    halo_tiles: int,
    mask_input_dir: Path | str = MASK_DIR,
    **db_config,
) -> Iterator[dict]:
    # --- Stage 1: Build the Mask Store (Disk-First) ---
    mask_store = {}
    print(f"Stage 1: Building mask store (Checking {mask_input_dir} then DB)...")
    for r0, r1, c0, c1 in tile_iter_over_bbox(global_bbox, pixel_size_deg, tile_px):
        mask_filename = f"{REGION}_tile_{r0}_{c0}_{RES_SUFFIX}.tif"
        mask_path = MASK_DIR / mask_filename
        if mask_path.exists():
            with rasterio.open(mask_path) as src:
                # Read band 1. Result is 2D (H, W)
                mask_data = src.read(1)
                # If it's 3D (1, H, W), squeeze it
                if mask_data.ndim == 3:
                    mask_data = mask_data[0]
                mask_store[(r0, c0)] = {"tile_mask": mask_data}
        else:
            # Fallback to DB if file is missing
            print(f"  Missing {mask_filename}, querying database...")
            mask_store[(r0, c0)] = build_mask_tile(
                r0, r1, c0, c1, pixel_size_deg, overlap_px, **db_config
            )
    print(f"Done! Loaded {len(mask_store)} masks into memory.")
    # --- Stage 2 & 3: Grouped Distance ---
    block_px = tile_px * block_tiles
    halo_px = tile_px * halo_tiles
    for br0, br1, bc0, bc1 in tile_iter_over_bbox(
        global_bbox, pixel_size_deg, block_px
    ):
        mr0, mr1, mc0, mc1 = br0 - halo_px, br1 + halo_px, bc0 - halo_px, bc1 + halo_px
        mosaic_h, mosaic_w = mr1 - mr0, mc1 - mc0
        mosaic = np.zeros((mosaic_h, mosaic_w), dtype=np.uint8)
        for tr0 in range(mr0, mr1, tile_px):
            for tc0 in range(mc0, mc1, tile_px):
                tile = mask_store.get((tr0, tc0))
                if tile:
                    m = tile["tile_mask"]
                    h, w = m.shape
                    r, c = tr0 - mr0, tc0 - mc0
                    # Prevent overflow on edges
                    r_end, c_end = min(r + h, mosaic_h), min(c + w, mosaic_w)
                    mosaic[r:r_end, c:c_end] = np.maximum(
                        mosaic[r:r_end, c:c_end], m[0 : r_end - r, 0 : c_end - c]
                    )
        # --- Stage 3: Float Distance ---
        if not mosaic.any():
            # Use NaN for empty areas; float32 supports this perfectly
            dist_mosaic = np.full(mosaic.shape, np.nan, dtype=np.float32)
        else:
            m_bbox = window_to_bbox(mr0, mr1, mc0, mc1, pixel_size_deg)
            transform = from_bounds(*m_bbox, mosaic_w, mosaic_h)
            dist_mosaic = calculate_distance(mosaic, transform)
        # --- Stage 4: Yield ---
        for tr0 in range(br0, br1, tile_px):
            for tc0 in range(bc0, bc1, tile_px):
                if (tr0, tc0) in mask_store:
                    tr1, tc1 = tr0 + tile_px, tc0 + tile_px
                    yield {
                        "tile_row0": tr0,
                        "tile_col0": tc0,
                        "tile_dist": clip_array_to_window(
                            dist_mosaic, mr0, mc0, tr0, tr1, tc0, tc1
                        ),
                        "tile_bbox": window_to_bbox(tr0, tr1, tc0, tc1, pixel_size_deg),
                    }
