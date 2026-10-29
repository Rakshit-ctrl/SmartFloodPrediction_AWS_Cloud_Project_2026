import numpy as np
import onnxruntime as ort
from PIL import Image

from .base import ModelMeta, ModelOutputError, SegmentationModel


class OnnxSegmentationModel(SegmentationModel):
    def __init__(self, meta: ModelMeta, weights_path):
        self.meta = meta
        self.session = ort.InferenceSession(str(weights_path), providers=["CPUExecutionProvider"])
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        shape = inp.shape  # e.g. [1, 3, 512, 512]; entries may be strings/None for dynamic axes
        if len(shape) != 4:
            raise ValueError(f"model input must be 4-D (N, C, H, W), got {shape}")
        expected = [meta.input.channels, meta.input.height, meta.input.width]
        for declared, wanted, axis in zip(shape[1:], expected, ("channels", "height", "width")):
            if isinstance(declared, int) and declared != wanted:
                raise ValueError(f"model.json input {axis}={wanted} but the ONNX model declares {declared}")

    # ---- preprocessing ----
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        spec = self.meta.input
        h, w, c = image.shape
        if getattr(spec, "normalization", "mean_std") == "percentile_sar":
            # Multi-band SAR input (normalized float32)
            if (w, h) != (spec.width, spec.height):
                chans = []
                for ch in range(c):
                    pil_ch = Image.fromarray(image[..., ch])
                    pil_ch = pil_ch.resize((spec.width, spec.height), Image.BILINEAR)
                    chans.append(np.asarray(pil_ch, dtype=np.float32))
                x = np.stack(chans, axis=-1)
            else:
                x = image.astype(np.float32)
            return np.ascontiguousarray(np.transpose(x, (2, 0, 1))[None], dtype=np.float32)

        pil = Image.fromarray(image if c == 3 else image[..., 0])
        pil = pil.resize((spec.width, spec.height), Image.BILINEAR)
        x = np.asarray(pil, dtype=np.float32)
        if c == 1:
            x = x[..., None]
        mean = np.array(spec.mean, dtype=np.float32).reshape(1, 1, c)
        std = np.array(spec.std, dtype=np.float32).reshape(1, 1, c)
        x = (x / spec.scale - mean) / std
        return np.ascontiguousarray(np.transpose(x, (2, 0, 1))[None], dtype=np.float32)

    # ---- postprocessing ----
    def _postprocess(self, out: np.ndarray, size: tuple[int, int]) -> np.ndarray:
        h, w = size
        spec = self.meta.output
        o = np.asarray(out)
        if o.ndim == 4:
            if o.shape[0] != 1:
                raise ModelOutputError(f"expected batch size 1, got output shape {o.shape}")
            o = o[0]
        if spec.type == "multiclass_logits":
            if o.ndim != 3 or spec.flood_class_index >= o.shape[0]:
                raise ModelOutputError(f"output shape {np.asarray(out).shape} is not (1, C, H, W) with class index {spec.flood_class_index}")
            cls = np.argmax(o, axis=0).astype(np.uint8)
            cls = np.asarray(Image.fromarray(cls).resize((w, h), Image.NEAREST))
            return cls == spec.flood_class_index
        if o.ndim == 3 and o.shape[0] == 1:
            o = o[0]
        if o.ndim != 2:
            raise ModelOutputError(f"binary output must be (1, 1, H, W) or (1, H, W), got {np.asarray(out).shape}")
        probs = o.astype(np.float32)
        if spec.type == "binary_logits":
            probs = 1.0 / (1.0 + np.exp(-np.clip(probs, -50, 50)))
        probs = np.asarray(Image.fromarray(probs.astype(np.float32)).resize((w, h), Image.BILINEAR))
        return probs >= spec.threshold

    def predict(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        out = self.session.run(None, {self.input_name: self._preprocess(image)})[0]
        return self._postprocess(out, (h, w))
