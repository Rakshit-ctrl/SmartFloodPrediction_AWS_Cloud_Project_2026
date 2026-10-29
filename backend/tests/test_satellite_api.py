import numpy as np

from tests.helpers import FakeModel, decode_png, image_bytes, install


def post(client, content, name="a.png"):
    return client.post("/api/satellite/analyze", files={"file": (name, content, "application/octet-stream")})


def test_completed_result_has_mask_overlay_and_stats(client, monkeypatch):
    install(monkeypatch, FakeModel())
    r = post(client, image_bytes("PNG", color=(200, 50, 50)))
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "completed" and d["segmentation_available"] is True
    assert d["mask"]["flooded_pixels"] == 64 * 32 and d["mask"]["flooded_fraction"] == 0.5
    assert d["model"]["name"] == "synthetic-test-double" and d["inference_ms"] >= 0

    mask = np.asarray(decode_png(d["mask"]["png_base64"]))
    assert mask.shape == (64, 64) and (mask[:, :32] == 255).all() and (mask[:, 32:] == 0).all()

    overlay = decode_png(d["overlay_png_base64"]).convert("RGB")
    assert overlay.size == (64, 64)
    assert overlay.getpixel((0, 0)) != (200, 50, 50)  # flooded half is tinted
    assert overlay.getpixel((63, 0)) == (200, 50, 50)  # dry half is untouched


def test_area_not_invented_for_non_georeferenced_png(client, monkeypatch):
    install(monkeypatch, FakeModel())
    area = post(client, image_bytes("PNG")).json()["area"]
    assert area["available"] is False and area["flooded_area_km2"] is None and "georeferenc" in area["reason"]


def test_overlay_is_downscaled_but_mask_keeps_full_size(client, monkeypatch):
    monkeypatch.setenv("OVERLAY_MAX_PX", "64")
    install(monkeypatch, FakeModel())
    d = post(client, image_bytes("PNG", size=(128, 128))).json()
    assert d["overlay_size"] == {"width": 64, "height": 64}
    assert decode_png(d["mask"]["png_base64"]).size == (128, 128)
    assert d["mask"]["flooded_pixels"] == 128 * 64


def test_completed_analysis_is_persisted_as_metadata_only(client, monkeypatch):
    install(monkeypatch, FakeModel())
    post(client, image_bytes("PNG"), "scene.png")
    rows = client.get("/api/satellite/analyses").json()
    assert len(rows) == 1
    row = rows[0]
    assert row["filename"] == "scene.png" and row["flooded_pixels"] == 2048 and row["model_name"] == "synthetic-test-double"
    assert row["flooded_area_km2"] is None and row["created_at"].endswith(("Z", "+00:00"))
    assert not any("base64" in k or "png" in k for k in row)


def test_not_configured_is_not_persisted_and_invalid_still_rejected(client):
    assert post(client, image_bytes("PNG")).json()["status"] == "model_not_configured"
    assert client.get("/api/satellite/analyses").json() == []
    assert post(client, b"junk").status_code == 422


def test_filename_path_is_stripped(client, monkeypatch):
    install(monkeypatch, FakeModel())
    assert post(client, image_bytes("PNG"), "../../etc/scene.png").json()["filename"] == "scene.png"


# ---- channel handling ----
def test_rgba_is_sent_to_model_as_three_channels(client, monkeypatch):
    m = FakeModel(channels=3)
    install(monkeypatch, m)
    post(client, image_bytes("PNG", mode="RGBA", color=(1, 2, 3, 255)))
    assert m.seen == [(64, 64, 3)]


def test_grayscale_model_gets_one_channel(client, monkeypatch):
    m = FakeModel(channels=1)
    install(monkeypatch, m)
    assert post(client, image_bytes("PNG", mode="L", color=90)).status_code == 200
    assert m.seen == [(64, 64, 1)]


def test_channel_mismatch_is_rejected_both_ways(client, monkeypatch):
    install(monkeypatch, FakeModel(channels=1))
    r = post(client, image_bytes("PNG"))
    assert r.status_code == 422 and r.json()["code"] == "incompatible_image"
    install(monkeypatch, FakeModel(channels=3))
    r = post(client, image_bytes("PNG", mode="L", color=5))
    assert r.status_code == 422 and r.json()["code"] == "incompatible_image"
    install(monkeypatch, FakeModel(channels=2))
    r = post(client, image_bytes("PNG"))
    assert r.status_code == 422 and r.json()["code"] == "incompatible_image"


def test_two_channel_satellite_model_with_multiband_tiff(client, monkeypatch):
    from rasterio.io import MemoryFile

    m = FakeModel(channels=2)
    install(monkeypatch, m)

    # Synthetic 6-band int16 TIFF representing Track1 SAR imagery
    raw_data = np.full((6, 64, 64), 500, dtype=np.int16)
    with MemoryFile() as mem:
        with mem.open(driver="GTiff", width=64, height=64, count=6, dtype="int16") as dst:
            dst.write(raw_data)
        tiff_bytes = mem.read()

    r = post(client, tiff_bytes, "sar_tile.tif")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "completed"
    assert d["image"]["channels"] == 2
    assert d["image"]["mode"] == "multispectral_6band"
    assert any("bands 1 and 2 extracted" in w for w in d["image"]["warnings"])
    assert m.seen == [(64, 64, 2)]


# ---- inference failures are loud, safe, and not persisted ----
def test_model_exception_returns_500_without_leaking_details(client, monkeypatch):
    install(monkeypatch, FakeModel(error=RuntimeError("boom /secret/path")))
    r = post(client, image_bytes("PNG"))
    assert r.status_code == 500 and r.json()["code"] == "inference_failed"
    assert "boom" not in r.text and "secret" not in r.text
    assert client.get("/api/satellite/analyses").json() == []


def test_wrong_mask_shape_or_dtype_is_rejected(client, monkeypatch):
    for bad in (np.zeros((3, 3), dtype=bool), np.zeros((64, 64), dtype=np.uint8)):
        install(monkeypatch, FakeModel(result=bad))
        r = post(client, image_bytes("PNG"))
        assert r.status_code == 500 and r.json()["code"] == "inference_failed"
    assert client.get("/api/satellite/analyses").json() == []
