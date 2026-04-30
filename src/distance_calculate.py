import distancerasters as dr
import numpy as np
import rasterio
from pathlib import Path
from rasterio.transform import from_bounds
from src.utils.helpers import (
    CRS,
    MASK_DIR,
    REGION,
    RES_SUFFIX,
    PIXEL_SIZE_DEG,
    TILE_PX,
    OVERLAP_PX,
    BLOCK_TILES,
    HALO_TILES,
)
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
        "dtype": "float32",
        "crs": CRS,
        "transform": transform,
        "compress": "lzw",
        "nodata": -9999,
    }
    with rasterio.open(path, "w", **profile) as dst:
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
    mask_input_dir: Path | str = MASK_DIR,
    **db_config,
) -> Iterator[dict]:
    """
    Processes distance calculations using environment-defined tile and block sizes.
    """

    # --- Stage 1: Build the Mask Store ---
    mask_store = {}
    for r0, r1, c0, c1 in tile_iter_over_bbox(global_bbox, PIXEL_SIZE_DEG, TILE_PX):
        mask_filename = f"{REGION}_s{TILE_PX}_tile_{r0}_{c0}_{RES_SUFFIX}.tif"
        mask_path = Path(mask_input_dir) / mask_filename

        if mask_path.exists():
            with rasterio.open(mask_path) as src:
                mask_data = src.read(1)
                if mask_data.ndim == 3:
                    mask_data = mask_data[0]
                mask_store[(r0, c0)] = {"tile_mask": mask_data}
        else:
            mask_store[(r0, c0)] = build_mask_tile(
                r0, r1, c0, c1, PIXEL_SIZE_DEG, OVERLAP_PX, **db_config
            )

    # --- Stage 2: Grouped Distance Assembly ---
    halo_px = int(TILE_PX * HALO_TILES)
    block_px = TILE_PX * BLOCK_TILES

    for br0, br1, bc0, bc1 in tile_iter_over_bbox(
        global_bbox, PIXEL_SIZE_DEG, block_px
    ):
        mr0, mr1, mc0, mc1 = br0 - halo_px, br1 + halo_px, bc0 - halo_px, bc1 + halo_px
        mosaic_h, mosaic_w = mr1 - mr0, mc1 - mc0
        mosaic = np.zeros((mosaic_h, mosaic_w), dtype=np.uint8)

        search_r0 = (mr0 // TILE_PX) * TILE_PX
        search_r1 = ((mr1 + TILE_PX - 1) // TILE_PX) * TILE_PX
        search_c0 = (mc0 // TILE_PX) * TILE_PX
        search_c1 = ((mc1 + TILE_PX - 1) // TILE_PX) * TILE_PX

        for tr0 in range(search_r0, search_r1, TILE_PX):
            for tc0 in range(search_c0, search_c1, TILE_PX):
                tile = mask_store.get((tr0, tc0))
                if tile:
                    m = tile["tile_mask"]
                    r_off, c_off = tr0 - mr0, tc0 - mc0

                    mos_r0, mos_c0 = max(0, r_off), max(0, c_off)
                    mos_r1, mos_c1 = (
                        min(r_off + TILE_PX, mosaic_h),
                        min(c_off + TILE_PX, mosaic_w),
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
            m_bbox = window_to_bbox(mr0, mr1, mc0, mc1, PIXEL_SIZE_DEG)
            transform = from_bounds(*m_bbox, mosaic_w, mosaic_h)
            dist_mosaic = calculate_distance(mosaic, transform)

        # --- Stage 4: Yield Clipped Tiles ---
        for tr0 in range(br0, br1, TILE_PX):
            for tc0 in range(bc0, bc1, TILE_PX):
                if (tr0, tc0) in mask_store:
                    tr1, tc1 = tr0 + TILE_PX, tc0 + TILE_PX
                    yield {
                        "tile_row0": tr0,
                        "tile_col0": tc0,
                        "tile_dist": clip_array_to_window(
                            dist_mosaic, mr0, mc0, tr0, tr1, tc0, tc1
                        ),
                        "tile_bbox": window_to_bbox(tr0, tr1, tc0, tc1, PIXEL_SIZE_DEG),
                    }
