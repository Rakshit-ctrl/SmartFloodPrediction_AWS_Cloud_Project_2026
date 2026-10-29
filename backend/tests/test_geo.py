import io
import sys

import numpy as np
import pytest
from PIL import Image

from tests.helpers import FakeModel, image_bytes, install


def post(client, content, name="a.tif"):
    return client.post("/api/satellite/analyze", files={"file": (name, content, "application/octet-stream")})


def test_tiff_without_rasterio_gives_reason_not_a_number(client, monkeypatch):
    monkeypatch.setitem(sys.modules, "rasterio", None)
    install(monkeypatch, FakeModel())
    area = post(client, image_bytes("TIFF")).json()["area"]
    assert area["available"] is False and "rasterio" in area["reason"]


def geotiff(crs, transform, count=3):
    from rasterio.io import MemoryFile
    data = np.full((count, 64, 64), 120, dtype=np.uint8)
    opts = dict(driver="GTiff", width=64, height=64, count=count, dtype="uint8", interleave="pixel")
    if count == 3:
        opts["photometric"] = "RGB"
    if crs:
        opts.update(crs=crs, transform=transform)
    with MemoryFile() as mem:
        with mem.open(**opts) as dst:
            dst.write(data)
        return mem.read()


class TestWithRasterio:
    @pytest.fixture(autouse=True)
    def _need_rasterio(self):
        pytest.importorskip("rasterio")

    def test_projected_metres(self, client, monkeypatch):
        from rasterio.transform import from_origin
        install(monkeypatch, FakeModel())
        d = post(client, geotiff("EPSG:32644", from_origin(500000, 1400000, 10, 10))).json()
        assert d["status"] == "completed" and d["mask"]["flooded_pixels"] == 2048
        assert d["area"]["available"] is True and d["area"]["pixel_area_m2"] == 100.0
        assert d["area"]["flooded_area_km2"] == 0.2048  # 2048 px x 100 m2
        assert d["area"]["crs"] == "EPSG:32644"
        assert "lat" not in d and "lon" not in d  # no coordinates are invented or returned

    def test_projected_feet_is_converted_to_metres(self, client, monkeypatch):
        from rasterio.transform import from_origin
        install(monkeypatch, FakeModel())
        area = post(client, geotiff("EPSG:2272", from_origin(0, 0, 10, 10))).json()["area"]
        assert area["available"] is True
        assert area["pixel_area_m2"] == pytest.approx(100 * 0.3048**2, rel=1e-3)

    def test_geographic_crs_gives_no_area(self, client, monkeypatch):
        from rasterio.transform import from_origin
        install(monkeypatch, FakeModel())
        area = post(client, geotiff("EPSG:4326", from_origin(80, 13, 0.0001, 0.0001))).json()["area"]
        assert area["available"] is False and "geographic" in area["reason"]

    def test_plain_tiff_without_crs_gives_no_area(self, client, monkeypatch):
        install(monkeypatch, FakeModel())
        area = post(client, geotiff(None, None)).json()["area"]
        assert area["available"] is False and "coordinate reference system" in area["reason"]

    def test_pillow_only_tiff_has_no_area(self, client, monkeypatch):
        install(monkeypatch, FakeModel())
        buf = io.BytesIO()
        Image.new("RGB", (64, 64)).save(buf, format="TIFF")
        assert post(client, buf.getvalue()).json()["area"]["available"] is False
