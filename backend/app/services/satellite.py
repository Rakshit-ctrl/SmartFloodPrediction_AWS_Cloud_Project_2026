"""Satellite image analysis: validate, run the configured model, render outputs.

Segmentation here means 'pixels the model classes as flooded/water-like in this image'.
It is not a weather observation and not a future flood forecast.
"""
import logging
import os
from time import perf_counter

from ..config import settings
from ..errors import ApiError
from ..ml.base import ModelOutputError
from ..ml.registry import get_model
from .geo import estimate_flood_area
from .imaging import mask_image, overlay_mask, png_base64, to_array, validate_upload

logger = logging.getLogger(__name__)


def analyze_image(content: bytes, filename: str) -> dict:
    filename = os.path.basename(filename or "")[:255]
    v = validate_upload(content, filename)  # raises ApiError for any invalid/unsupported upload
    model, status = get_model()
    base = {
        "filename": filename,
        "bytes_received": len(content),
        "image": v.info(),
        "model": status.as_dict(),
    }
    if model is None:
        return {
            **base,
            "status": "model_not_configured",
            "segmentation_available": False,
            "mask": None,
            "message": f"The image is valid, but no segmentation model is available ({status.state}): {status.message}",
        }

    channels = model.meta.input.channels
    if v.channels != channels:
        raise ApiError(422, "incompatible_image", f"This model expects {channels}-channel imagery but the image has {v.channels} channel(s).")

    arr = v.raw_bands if v.raw_bands is not None else to_array(v.image)
    start = perf_counter()
    try:
        mask = model.predict(arr)
    except ModelOutputError as exc:
        raise ApiError(500, "inference_failed", f"Model output did not match model.json: {exc}")
    except Exception:
        logger.exception("Inference failed")
        raise ApiError(500, "inference_failed", "Model inference failed. See the server log for details.")
    inference_ms = round((perf_counter() - start) * 1000, 1)

    if getattr(mask, "dtype", None) != bool or getattr(mask, "shape", None) != arr.shape[:2]:
        logger.error("Model returned an invalid mask (dtype/shape mismatch)")
        raise ApiError(500, "inference_failed", "The model returned a mask with the wrong type or size.")

    flooded = int(mask.sum())
    total = int(mask.size)
    overlay = overlay_mask(v.image, mask, settings.overlay_max_px)
    return {
        **base,
        "status": "completed",
        "segmentation_available": True,
        "message": "Segmentation completed. Flooded pixels are the model's prediction for this image only; accuracy has not been validated here.",
        "mask": {
            "width": mask.shape[1],
            "height": mask.shape[0],
            "flooded_pixels": flooded,
            "total_pixels": total,
            "flooded_fraction": flooded / total,
            "png_base64": png_base64(mask_image(mask)),
        },
        "overlay_png_base64": png_base64(overlay),
        "overlay_size": {"width": overlay.width, "height": overlay.height},
        "area": estimate_flood_area(content, v.format, v.width, v.height, flooded),
        "inference_ms": inference_ms,
    }
