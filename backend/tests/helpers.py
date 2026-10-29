"""Shared SYNTHETIC test fixtures. Nothing here represents real satellite imagery or a real flood model."""
import base64
import io

import numpy as np
from PIL import Image

from app.ml.base import ModelMeta, SegmentationModel
from app.ml.registry import ModelStatus


def image_bytes(fmt="PNG", size=(64, 64), mode="RGB", color=(200, 50, 50)) -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format=fmt)
    return buf.getvalue()


def make_meta(channels=3, output_type="binary_logits") -> ModelMeta:
    return ModelMeta.model_validate({
        "name": "synthetic-test-double", "version": "0", "architecture": "none", "format": "onnx",
        "weights_file": "none.onnx",
        "input": {"width": 32, "height": 32, "channels": channels, "mean": [0.5] * channels, "std": [0.5] * channels},
        "output": {"type": output_type},
    })


class FakeModel(SegmentationModel):
    """SYNTHETIC TEST DOUBLE: marks the left half of any image. It says nothing about real floods."""

    def __init__(self, channels=3, result=None, error=None):
        self.meta = make_meta(channels)
        self.seen = []
        self._result, self._error = result, error

    def predict(self, image):
        self.seen.append(image.shape)
        if self._error:
            raise self._error
        if self._result is not None:
            return self._result
        m = np.zeros(image.shape[:2], dtype=bool)
        m[:, : image.shape[1] // 2] = True
        return m


def install(monkeypatch, model):
    status = ModelStatus("ready", "Model loaded.", name=model.meta.name, version=model.meta.version,
                         architecture=model.meta.architecture, weights_sha256="0" * 64)
    monkeypatch.setattr("app.services.satellite.get_model", lambda: (model, status))


def decode_png(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64)))
