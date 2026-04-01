import math
from typing import Tuple
import rasterio
from pathlib import Path
import numpy as np
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from src.query_ways import fetch_highways
from src.utils.helpers import (
    CRS,
    LON_MIN,
    LON_MAX,
    LAT_MIN,
    LAT_MAX,
    REGION,
    RES_SUFFIX,
)


# --- Write to Disk ---
def write_mask_geotiff(
    path: Path | str, arr: np.ndarray, bbox: Tuple[float, float, float, float]
):
    """Writes a 0/1 mask to a GeoTIFF."""
    h, w = arr.shape
    transform = from_bounds(*bbox, w, h)
    profile = {
        "driver": "GTiff",
        "height": h,
        "width": w,
        "count": 1,
        "dtype": "uint8",
        "crs": CRS,
        "transform": transform,
        "compress": "deflate",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)


# --- Global Grid Logic ---
def grid_shape(res_deg: float) -> tuple[int, int]:
    """
    Returns (width, height) of the entire 4326 world grid at this resolution.
    Used to ensure all tiles align to the same global pixel boundaries.
    """
    width = int(round((LON_MAX - LON_MIN) / res_deg))
    height = int(round((LAT_MAX - LAT_MIN) / res_deg))
    return width, height


def coords_to_rowcol(lon: float, lat: float, pixel_size_deg: float) -> tuple[int, int]:
    """Converts a geographic coordinate to a global pixel index."""
    col = int(math.floor((lon - LON_MIN) / pixel_size_deg))
    row = int(math.floor((LAT_MAX - lat) / pixel_size_deg))
    return row, col


def snap_direction(x: int, tile_px: int, direction: str) -> int:
    if direction == "down":
        return (x // tile_px) * tile_px
    if direction == "up":
        return ((x + tile_px - 1) // tile_px) * tile_px
    raise ValueError("direction must be 'down' or 'up'")


def window_to_bbox(
    row0: int, row1: int, col0: int, col1: int, res_deg: float
) -> Tuple[float, float, float, float]:
    """Converts pixel window back to Lon/Lat BBox, anchored to the global origin."""
    xmin = LON_MIN + col0 * res_deg
    xmax = LON_MIN + col1 * res_deg
    ymax = LAT_MAX - row0 * res_deg
    ymin = LAT_MAX - row1 * res_deg
    return (xmin, ymin, xmax, ymax)


# --- Tile & Block Orchestration ---
def tile_iter_over_bbox(bbox, pixel_size_deg, tile_px):
    min_lon, min_lat, max_lon, max_lat = bbox
    row_top, col_left = coords_to_rowcol(min_lon, max_lat, pixel_size_deg)
    row_bot, col_right = coords_to_rowcol(max_lon, min_lat, pixel_size_deg)
    # Snap to tile boundaries
    row0 = snap_direction(min(row_top, row_bot), tile_px, "down")
    row1 = snap_direction(max(row_top, row_bot) + 1, tile_px, "up")
    col0 = snap_direction(min(col_left, col_right), tile_px, "down")
    col1 = snap_direction(max(col_left, col_right) + 1, tile_px, "up")
    # Iterate
    for r0 in range(row0, row1, tile_px):
        for c0 in range(col0, col1, tile_px):
            yield (r0, r0 + tile_px, c0, c0 + tile_px)


def tile_count_over_bbox(bbox, pixel_size_deg, tile_px):
    """Returns (nx, ny, total) tiles needed to cover the area."""
    it = list(tile_iter_over_bbox(bbox, pixel_size_deg, tile_px))
    rows = set(t[0] for t in it)
    cols = set(t[2] for t in it)
    return len(cols), len(rows), len(it)


# --- Raster & Mask Logic ---
def rasterize_geoms(geoms, bbox, pixel_size_deg, all_touched=True):
    xmin, ymin, xmax, ymax = bbox
    w, h = (
        int(round((xmax - xmin) / pixel_size_deg)),
        int(round((ymax - ymin) / pixel_size_deg)),
    )
    transform = from_bounds(xmin, ymin, xmax, ymax, w, h)
    valid_geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not valid_geoms:
        return np.zeros((h, w), dtype=np.uint8), transform
    arr = rasterize(
        [(g, 1) for g in valid_geoms],
        out_shape=(h, w),
        transform=transform,
        fill=0,
        dtype=np.uint8,
        all_touched=all_touched,
    )
    return arr, transform


def clip_array_to_window(
    arr, src_row0, src_col0, dst_row0, dst_row1, dst_col0, dst_col1
):
    r0, r1 = dst_row0 - src_row0, dst_row1 - src_row0
    c0, c1 = dst_col0 - src_col0, dst_col1 - src_col0
    return arr[r0:r1, c0:c1]


def build_mask_tile(row0, row1, col0, col1, pixel_size_deg, overlap_px, db_config):
    # Expand for query
    row0e, row1e, col0e, col1e = (
        row0 - overlap_px,
        row1 + overlap_px,
        col0 - overlap_px,
        col1 + overlap_px,
    )
    bbox_expanded = window_to_bbox(row0e, row1e, col0e, col1e, pixel_size_deg)
    # Query Database
    roads_data = fetch_highways(bbox_tile=bbox_expanded, **db_config)
    geoms = [g for g, tag in roads_data]
    # Rasterize
    mask_expanded, _ = rasterize_geoms(geoms, bbox_expanded, pixel_size_deg)
    # Clip back to core tile
    tile_mask = clip_array_to_window(
        mask_expanded, row0e, col0e, row0, row1, col0, col1
    )
    tile_bbox = window_to_bbox(row0, row1, col0, col1, pixel_size_deg)
    return {
        "tile_mask": tile_mask,
        "tile_bbox": tile_bbox,
        "roads_count": len(roads_data),
    }


# --- Complete Mask Flow ---
def generate_mask_tiles(
    global_bbox: Tuple[float, float, float, float],
    pixel_size_deg: float,
    tile_px: int,
    overlap_px: int,
    output_dir: str,
    db_config: dict,
):
    """
    Orchestrates the query and rasterization for a region.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Tile Computation for Progress Logging
    nx, ny, total = tile_count_over_bbox(global_bbox, pixel_size_deg, tile_px)
    print(f"Global Grid: {grid_shape(pixel_size_deg)}")
    print(f"Region: {nx}x{ny} tiles ({total} total)")
    # Iterate and Process Raster
    for r0, r1, c0, c1 in tile_iter_over_bbox(global_bbox, pixel_size_deg, tile_px):
        # build_mask_tile handles the expanded query and the clip back to core tile_px
        tile_data = build_mask_tile(
            r0, r1, c0, c1, pixel_size_deg, overlap_px, db_config
        )
        mask = tile_data["tile_mask"]
        bbox = tile_data["tile_bbox"]
        # Saving ONLY if roads exists (optional optimization)
        if mask.any():
            filename = f"{REGION}_tile_{r0}_{c0}_{RES_SUFFIX}.tif"
            filepath = output_path / filename
            write_mask_geotiff(filepath, mask, bbox)
            print(f"Saved: {filename} ({tile_data['roads_count']} roads)")
        else:
            print(f"Skipping empty tile: {r0}_{c0}")
