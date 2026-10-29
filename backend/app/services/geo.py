"""Flood-area estimation from GeoTIFF georeferencing. Optional: needs rasterio.

An area is reported only when the raster has a projected CRS and a valid transform whose size
matches the decoded image. Otherwise a reason is returned and no number is invented.
"""
import warnings


def _no(reason: str) -> dict:
    return {"available": False, "flooded_area_km2": None, "pixel_area_m2": None, "crs": None, "reason": reason}


def estimate_flood_area(content: bytes, fmt: str, width: int, height: int, flooded_pixels: int) -> dict:
    if fmt != "TIFF":
        return _no("This image format carries no georeferencing; only GeoTIFF does.")
    try:
        from rasterio.io import MemoryFile
    except ImportError:
        return _no("rasterio is not installed, so GeoTIFF georeferencing cannot be read. Run: pip install -r requirements-geo.txt")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # NotGeoreferencedWarning for plain TIFFs
            with MemoryFile(content) as mem, mem.open() as src:
                crs, transform, w, h = src.crs, src.transform, src.width, src.height
    except Exception:
        return _no("The GeoTIFF georeferencing metadata could not be read.")
    if crs is None:
        return _no("The TIFF has no coordinate reference system (not georeferenced).")
    if (w, h) != (width, height):
        return _no("Raster size and decoded image size disagree; area not estimated.")
    if not crs.is_projected:
        return _no("The CRS is geographic (degrees). Reproject to a projected CRS in linear units before analysis to get areas.")
    _, to_metres = crs.linear_units_factor
    det = abs(transform.a * transform.e - transform.b * transform.d)
    if det == 0:
        return _no("The raster transform is degenerate; area not estimated.")
    pixel_area_m2 = det * to_metres**2
    return {
        "available": True,
        "flooded_area_km2": round(flooded_pixels * pixel_area_m2 / 1e6, 4),
        "pixel_area_m2": round(pixel_area_m2, 4),
        "crs": crs.to_string(),
        "reason": None,
    }
