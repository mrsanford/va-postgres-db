# compute.py
import os
from tile_rasterize import (
    window_to_bbox,
    write_geotiff,
    rasterize_bbox,
    calculate_distance,
    tile_count_over_bbox,
    tile_iter_over_bbox,
)


def main() -> None:
    pixel_size_deg = 0.002
    tile_px = 256
    VA_BBOX = (-83.7, 36.5, -75.2, 39.5)

    out_dir = "./va_tiles"
    os.makedirs(out_dir, exist_ok=True)

    nx, ny, nt = tile_count_over_bbox(VA_BBOX, pixel_size_deg, tile_px)
    print(f"Virginia tiles: nx={nx}, ny={ny}, total={nt}")

    written = 0
    seen = 0
    for row0, row1, col0, col1 in tile_iter_over_bbox(VA_BBOX, pixel_size_deg, tile_px):
        seen += 1
        bbox_tile = window_to_bbox(row0, row1, col0, col1, pixel_size_deg)

        mask, transform, roads, mask_sum = rasterize_bbox(
            bbox_tile, pixel_size_deg, all_touched=True
        )
        # Skip tiles with no roads
        if not mask.any():
            continue
        # 1) write mask
        # mask_path = os.path.join(out_dir, f"va_mask_r{row0}_c{col0}.tif")
        # write_geotiff(mask_path, mask, bbox_tile, dtype="uint8", nodata=0)
        # 2) compute + write distance
        dist = calculate_distance(mask, transform)
        dist_path = os.path.join(out_dir, f"va_dist_r{row0}_c{col0}.tif")
        write_geotiff(dist_path, dist, bbox_tile, dtype="float32", nodata=None)
        written += 1
        if written % 10 == 0:
            print(
                f"[seen {seen}/{nt}] [written {written}] "
                f"last=r{row0} c{col0} roads={roads} sum={mask_sum}"
            )
    print(f"Done. Wrote {written} non-empty mask+distance tile pairs to {out_dir}")


if __name__ == "__main__":
    main()

# rasterize roads mask in EPSG:4326 (or directly fetch geometries and reproject)
# reproject tile+halo to a projected CRS (UTM zone(s) or EPSG:3857)
# compute distance in that projected CRS (units = meters)
# reproject distance back to EPSG:4326 (optional) or keep projected output
