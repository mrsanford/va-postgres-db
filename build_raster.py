import distancerasters as dr
from query_ways import fetch_highways


def compute_bounds(vectors: list):
    minx = min(g.bounds[0] for g in vectors)
    miny = min(g.bounds[1] for g in vectors)
    maxx = max(g.bounds[2] for g in vectors)
    maxy = max(g.bounds[3] for g in vectors)
    return (minx, miny, maxx, maxy)


def build_distance_raster(pixel_size=0.01, output_path="./va-highway-distance.tif"):
    roads = fetch_highways()
    vectors = [geom for geom, tag in roads]
    bounds = compute_bounds(vectors)
    rv_array, affine = dr.rasterize(
        vectors,
        pixel_size=0.01,
        bounds=bounds,
    )

    def raster_conditional(rarray):
        return rarray == 1

    dr_obj = dr.DistanceRaster(
        rv_array,
        affine=affine,
        conditional=raster_conditional,
        output_path="./va-highways-distance.tif",
    )

    return dr_obj.dist_array


if __name__ == "__main__":
    dist = build_distance_raster()
