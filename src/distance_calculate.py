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


def process_region_grouped_distance(
    global_bbox: Tuple[float, float, float, float],
    pixel_size_deg: float,
    tile_px: int,
    overlap_px: int,
    block_tiles: int,
    halo_tiles: float,  # fractional halo (e.g., 0.8)
    mask_input_dir: Path | str = MASK_DIR,
    **db_config,
) -> Iterator[dict]:

    # --- Stage 1: Build the Mask Store ---
    mask_store = {}
    for r0, r1, c0, c1 in tile_iter_over_bbox(global_bbox, pixel_size_deg, tile_px):
        mask_filename = f"{REGION}_s{tile_px}_tile_{r0}_{c0}_{RES_SUFFIX}.tif"
        mask_path = Path(mask_input_dir) / mask_filename
        if mask_path.exists():
            with rasterio.open(mask_path) as src:
                mask_data = src.read(1)
                if mask_data.ndim == 3:
                    mask_data = mask_data[0]
                mask_store[(r0, c0)] = {"tile_mask": mask_data}
        else:
            mask_store[(r0, c0)] = build_mask_tile(
                r0, r1, c0, c1, pixel_size_deg, overlap_px, **db_config
            )

    # --- Stage 2: Grouped Distance Assembly ---
    halo_px = int(tile_px * halo_tiles)
    block_px = tile_px * block_tiles

    for br0, br1, bc0, bc1 in tile_iter_over_bbox(
        global_bbox, pixel_size_deg, block_px
    ):
        # Define mosaic boundaries including the fractional overhang
        mr0, mr1, mc0, mc1 = br0 - halo_px, br1 + halo_px, bc0 - halo_px, bc1 + halo_px
        mosaic_h, mosaic_w = mr1 - mr0, mc1 - mc0
        mosaic = np.zeros((mosaic_h, mosaic_w), dtype=np.uint8)

        # Snap search bounds to ensure we grab all tiles touching the fractional halo
        search_r0 = (mr0 // tile_px) * tile_px
        search_r1 = ((mr1 + tile_px - 1) // tile_px) * tile_px
        search_c0 = (mc0 // tile_px) * tile_px
        search_c1 = ((mc1 + tile_px - 1) // tile_px) * tile_px

        for tr0 in range(search_r0, search_r1, tile_px):
            for tc0 in range(search_c0, search_c1, tile_px):
                tile = mask_store.get((tr0, tc0))
                if tile:
                    m = tile["tile_mask"]
                    # Calculate tile's top-left position relative to mosaic top-left
                    r_off, c_off = tr0 - mr0, tc0 - mc0

                    # Safe Slicing: Determine overlap between tile and mosaic
                    # This handles cases where only a fraction of a tile is inside the halo
                    mos_r0, mos_c0 = max(0, r_off), max(0, c_off)
                    mos_r1, mos_c1 = (
                        min(r_off + tile_px, mosaic_h),
                        min(c_off + tile_px, mosaic_w),
                    )

                    mask_r0, mask_c0 = max(0, -r_off), max(0, -c_off)
                    mask_r1 = mask_r0 + (mos_r1 - mos_r0)
                    mask_c1 = mask_c0 + (mos_c1 - mos_c0)

                    mosaic[mos_r0:mos_r1, mos_c0:mos_c1] = np.maximum(
                        mosaic[mos_r0:mos_r1, mos_c0:mos_c1],
                        m[mask_r0:mask_r1, mask_c0:mask_c1],
                    )

        # --- Stage 3: Float Distance Calculation ---
        if not mosaic.any():
            dist_mosaic = np.full(mosaic.shape, np.nan, dtype=np.float32)
        else:
            m_bbox = window_to_bbox(mr0, mr1, mc0, mc1, pixel_size_deg)
            transform = from_bounds(*m_bbox, mosaic_w, mosaic_h)
            dist_mosaic = calculate_distance(mosaic, transform)

        # --- Stage 4: Yield Clipped Tiles ---
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
