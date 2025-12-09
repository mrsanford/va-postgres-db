import math
import numpy as np
import distancerasters as dr
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from shapely.geometry import box
from query_ways import fetch_highways


def km_degrees_calc(km: float, latitude: float = 38.0):
    """
    Converts km to lat/lon degrees at a given latitude
    """
    lat_deg_per_km = 1.0 / 111.32
    lon_deg_per_km = 1.0 / (111.32 * math.cos(math.radians(latitude)))
    return km * lat_deg_per_km, km * lon_deg_per_km


def compute_bounds(vectors: list):
    """
    Gets overall bounding box covering all geometries
    """
    minx = min(g.bounds[0] for g in vectors)
    miny = min(g.bounds[1] for g in vectors)
    maxx = max(g.bounds[2] for g in vectors)
    maxy = max(g.bounds[3] for g in vectors)
    return minx, miny, maxx, maxy


def clip_geometries(geoms, bbox):
    """
    Only returns geometries that intersect the bbox
    """
    minx, miny, maxx, maxy = bbox
    region_box = box(minx, miny, maxx, maxy)
    return [g for g in geoms if g.intersects(region_box)]


def expand_bounds(minx: float, miny: float, maxx: float, maxy: float, buffer_km: float):
    """
    Expands a bounding box by buffer_km in all directions.
    """
    mid_lat = (miny + maxy) / 2.0
    lat_buf, lon_buf = km_degrees_calc(buffer_km, latitude=mid_lat)
    return (minx - lon_buf, miny - lat_buf, maxx + lon_buf, maxy + lat_buf)


def build_distance_raster(
    pixel_km: float = 1.0,
    buffer_km: float = 5.0,
    output_path="./va-highway-distance-blackstone.tif",
):
    """
    Builds a distance-to-highway raster
    Optional: expand the bounding box by buffer_km outward
    """

    # fetch road vectors
    roads = fetch_highways()
    print("highway test", len(roads))

    for i, (geom, tag) in enumerate(roads[:5]):
        print(f"{i}: highway={tag}, geom_type={geom.geom_type}, bounds={geom.bounds}")
    vectors = [geom for geom, tag in roads]

    # compute initial bounding box
    # minx, miny, maxx, maxy = compute_bounds(vectors)

    # getting Richmond, C-ville, Blackstone ROI
    va_bbox = (-78.3648, 36.7940, -77.6408, 37.3720)
    vector_clip = clip_geometries(vectors, va_bbox)
    minx, miny, maxx, maxy = va_bbox

    # expand bounding box
    if buffer_km > 0:
        minx, miny, maxx, maxy = expand_bounds(minx, miny, maxx, maxy, buffer_km)
    # pixel size in degrees
    mid_lat = (miny + maxy) / 2.0
    pixel_lat_deg, pixel_lon_deg = km_degrees_calc(pixel_km, latitude=mid_lat)
    # raster size
    rows = math.ceil((maxy - miny) / pixel_lat_deg)
    cols = math.ceil((maxx - minx) / pixel_lon_deg)

    transform = from_bounds(minx, miny, maxx, maxy, cols, rows)
    rv_array = rasterize(
        [(geom, 1) for geom in vector_clip],
        out_shape=(rows, cols),
        transform=transform,
        fill=0,
        dtype=np.uint8,
    )

    # the distance function
    def raster_conditional(rarray):
        return rarray == 1

    # computing distance raster
    dr_obj = dr.DistanceRaster(
        rv_array,
        affine=transform,
        conditional=raster_conditional,
        output_path=output_path,
    )
    return dr_obj.dist_array


if __name__ == "__main__":
    dist = build_distance_raster(
        pixel_km=1.0,
        buffer_km=10.0,
    )
