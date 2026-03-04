import math
import numpy as np
import rasterio
from typing import Tuple
import distancerasters as dr
from rasterio.transform import from_bounds
from rasterio.features import rasterize
from query_ways import fetch_highways

CRS = "EPSG:4326"
LON_MIN, LON_MAX = -180.0, 180.0
LAT_MIN, LAT_MAX = -90.0, 90.0


def grid_shape(res_deg: float) -> tuple[int, int]:
    """
    Getting global raster grid shape (width, height) for EPSG 4326 in
    pixel resolution in degrees
    ---
    Returns:
        (width, height) in pixels
    """
    width = int(round((LON_MAX - LON_MIN) / res_deg))
    height = int(round((LAT_MAX - LAT_MIN) / res_deg))
    return width, height


def snap_direction(x, tile_px, direction: str):
    """
    Snaps integer pixel index to tile grid boundary
    Returns:
        Snapped index as integer multiple of tile_px
    """
    if direction == "down":
        return (x // tile_px) * tile_px
    elif direction == "up":
        return ((x + tile_px - 1) // tile_px) * tile_px
    else:
        raise ValueError(f"direction must be 'down' or 'up', got {direction!r}")


def window_to_bbox(
    row0: int,
    row1: int,
    col0: int,
    col1: int,
    res_deg: float,
    lon_min: float = LON_MIN,
    lat_max: float = LAT_MAX,
) -> Tuple[float, float, float, float]:
    """
    Converts a pixel window (row/col indices) into a geographic bounding box
    in EPSG:4326.
    ---
    Returns:
        (xmin, ymin, xmax, ymax) in degrees.
    """
    xmin = lon_min + col0 * res_deg
    xmax = lon_min + col1 * res_deg
    ymax = lat_max - row0 * res_deg
    ymin = lat_max - row1 * res_deg
    return (xmin, ymin, xmax, ymax)


def rasterize_bbox(
    bbox: Tuple[float, float, float, float],
    pixel_size_deg: float,
    all_touched: bool = True,
):
    """
    Queries OSM highways intersecting a bbox and rasterizes into 0/1 mask.
    ---
    Args:
        bbox: (xmin, ymin, xmax, ymax) in EPSG:4326.
        pixel_size_deg: Pixel resolution in degrees.
        all_touched: If True, burn any pixel touched by a line.
    Returns:
        arr: 2D uint8 mask (1 = road, 0 = no road)
        road_count: Number of vector road features returned
        mask_sum: Total number of road pixels (sum of array)
    """
    xmin, ymin, xmax, ymax = bbox
    # w = int(math.ceil((xmax - xmin) / pixel_size_deg))
    # h = int(math.ceil((ymax - ymin) / pixel_size_deg))
    w = int(round((xmax - xmin) / pixel_size_deg))
    h = int(round((ymax - ymin) / pixel_size_deg))
    roads = fetch_highways(bbox_tile=bbox)
    geoms = [g for (g, tag) in roads if g is not None and not g.is_empty]
    transform = from_bounds(xmin, ymin, xmax, ymax, w, h)
    if not geoms:
        return np.zeros((h, w), dtype=np.uint8), transform, len(roads), 0
    arr = rasterize(
        [(g, 1) for g in geoms],
        out_shape=(h, w),
        transform=transform,
        fill=0,
        dtype=np.uint8,
        all_touched=all_touched,
    )
    return arr, transform, len(roads), int(arr.sum())


def write_geotiff(
    path: str,
    arr: np.ndarray,
    bbox: Tuple[float, float, float, float],
    dtype=None,
    nodata=None,
):
    """
    Writes single-band raster array to disk as GeoTIFF in EPSG:4326
    """
    if arr.ndim != 2:
        raise ValueError("write_geotiff expects a 2D array.")
    h, w = arr.shape
    transform = from_bounds(*bbox, w, h)
    if dtype is None:
        dtype = str(arr.dtype)
    profile = dict(
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype=dtype,
        crs=CRS,
        transform=transform,
        compress="DEFLATE",
        nodata=nodata,
    )
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr, 1)


def calculate_distance(
    rv_array: np.ndarray,
    transform,
    output_path: str | None = None,
) -> np.ndarray:
    """
    Computes the distance-to-road from the binary mask.
    ---
    Args:
        rv_array:
            2D array where 1 = road, 0 = non-road.
        transform:
            Affine transform for spatial referencing.
        output_path:
            Optional file path. If None, distance is not written to disk.
    Returns:
        2D float32 distance array.
    """
    if rv_array.ndim != 2:
        raise ValueError("Distance input must be 2D.")

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


def coords_to_rowcol(lon: float, lat: float, pixel_size_deg: float) -> tuple[int, int]:
    """
    Convert lon/lat (EPSG:4326) to global raster row/col indices.
    """
    col = int(math.floor((lon - LON_MIN) / pixel_size_deg))
    row = int(math.floor((LAT_MAX - lat) / pixel_size_deg))
    return row, col


def tile_iter_over_bbox(bbox, pixel_size_deg, tile_px):
    """
    Yield tile windows (row0,row1,col0,col1) that fully cover a bbox.
    bbox = (min_lon, min_lat, max_lon, max_lat) in EPSG:4326
    yields (row0,row1,col0,col1)
    """
    min_lon, min_lat, max_lon, max_lat = bbox

    row_top, col_left = coords_to_rowcol(min_lon, max_lat, pixel_size_deg)
    row_bot, col_right = coords_to_rowcol(max_lon, min_lat, pixel_size_deg)

    row_min = min(row_top, row_bot)
    row_max = max(row_top, row_bot)
    col_min = min(col_left, col_right)
    col_max = max(col_left, col_right)

    # snap outward to fully cover
    row0 = snap_direction(row_min, tile_px, "down")
    col0 = snap_direction(col_min, tile_px, "down")
    row1 = snap_direction(
        row_max + 1, tile_px, "up"
    )  # +1 to include last touched pixel
    col1 = snap_direction(col_max + 1, tile_px, "up")

    for r0 in range(row0, row1, tile_px):
        for c0 in range(col0, col1, tile_px):
            yield (r0, r0 + tile_px, c0, c0 + tile_px)


def tile_count_over_bbox(bbox, pixel_size_deg, tile_px):
    """
    Count how many tiles (tile_px x tile_px) are required to cover a bbox.
    Returns:
        (n_tiles_x, n_tiles_y, n_tiles_total)"""
    min_lon, min_lat, max_lon, max_lat = bbox
    row_top, col_left = coords_to_rowcol(min_lon, max_lat, pixel_size_deg)
    row_bot, col_right = coords_to_rowcol(max_lon, min_lat, pixel_size_deg)

    row_min = min(row_top, row_bot)
    row_max = max(row_top, row_bot)
    col_min = min(col_left, col_right)
    col_max = max(col_left, col_right)

    row0 = snap_direction(row_min, tile_px, "down")
    col0 = snap_direction(col_min, tile_px, "down")
    row1 = snap_direction(row_max + 1, tile_px, "up")
    col1 = snap_direction(col_max + 1, tile_px, "up")

    n_y = (row1 - row0) // tile_px
    n_x = (col1 - col0) // tile_px
    return n_x, n_y, n_x * n_y
