import io

import pytest
from PIL import Image

from tests.helpers import image_bytes


def post(client, content, name="a.png"):
    return client.post("/api/satellite/analyze", files={"file": (name, content, "application/octet-stream")})


def test_valid_png_jpeg_tiff_accepted_without_model(client):
    for fmt, name in (("PNG", "a.png"), ("JPEG", "a.jpg"), ("TIFF", "a.tif")):
        r = post(client, image_bytes(fmt), name)
        assert r.status_code == 200, (fmt, r.text)
        d = r.json()
        assert d["status"] == "model_not_configured" and d["segmentation_available"] is False and d["mask"] is None
        assert d["image"]["width"] == 64 and d["image"]["format"] == fmt and d["model"]["state"] == "not_configured"


def test_garbage_bytes_with_image_extension_rejected(client):
    r = post(client, b"123")
    assert r.status_code == 422 and r.json()["code"] == "invalid_image"


def test_empty_file_rejected(client):
    r = post(client, b"")
    assert r.status_code == 400 and r.json()["code"] == "empty_file"


def test_extension_must_match_content(client):
    r = post(client, image_bytes("JPEG"), "a.png")
    assert r.status_code == 415 and r.json()["code"] == "extension_mismatch"


def test_truncated_png_rejected(client):
    r = post(client, image_bytes("PNG", size=(256, 256))[:300])
    assert r.status_code == 422 and r.json()["code"] == "invalid_image"


def test_pixel_limit_enforced_before_decoding(client, monkeypatch):
    monkeypatch.setenv("MAX_IMAGE_PIXELS", "1000")
    r = post(client, image_bytes("PNG", size=(64, 64)))
    assert r.status_code == 413 and r.json()["code"] == "image_too_large"


def test_tiny_image_rejected(client):
    r = post(client, image_bytes("PNG", size=(16, 64)))
    assert r.status_code == 422 and r.json()["code"] == "image_too_small"


@pytest.mark.parametrize("mode,color", [("I;16", 1000), ("F", 1.5), ("CMYK", (0, 0, 0, 0))])
def test_unsupported_modes_rejected_with_clear_message(client, mode, color):
    buf = io.BytesIO()
    Image.new(mode, (64, 64), color).save(buf, format="TIFF")
    r = post(client, buf.getvalue(), "a.tif")
    assert r.status_code == 422 and r.json()["code"] == "unsupported_image_mode"
    assert "8-bit" in r.json()["detail"]


def test_rgba_and_palette_are_accepted_and_reported(client):
    d = post(client, image_bytes("PNG", mode="RGBA", color=(1, 2, 3, 128))).json()
    assert d["image"]["mode"] == "RGBA" and d["image"]["channels"] == 3
    assert any("Alpha" in w for w in d["image"]["warnings"])
    buf = io.BytesIO()
    Image.new("P", (64, 64), 3).save(buf, format="PNG")
    assert post(client, buf.getvalue()).json()["image"]["channels"] == 3


def test_grayscale_is_one_channel(client):
    assert post(client, image_bytes("PNG", mode="L", color=100)).json()["image"]["channels"] == 1
