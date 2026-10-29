"""Upload validation, decoding, and overlay rendering. Pillow + numpy only."""
import base64
import io
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

from ..config import settings
from ..errors import ApiError

EXT_FORMAT = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG", "tif": "TIFF", "tiff": "TIFF"}
MIN_SIDE = 32
OVERLAY_COLOR = (0, 120, 255)
OVERLAY_ALPHA = 0.45


@dataclass
class ValidatedImage:
    image: Image.Image  # decoded, mode "RGB" or "L"
    format: str  # PNG | JPEG | TIFF
    original_mode: str
    warnings: list[str] = field(default_factory=list)
    raw_bands: np.ndarray | None = None  # (H, W, 2) float32 if multi-band satellite TIFF

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    @property
    def channels(self) -> int:
        if self.raw_bands is not None:
            return self.raw_bands.shape[-1]
        return 1 if self.image.mode == "L" else 3

    def info(self) -> dict:
        return {
            "width": self.width, "height": self.height, "format": self.format,
            "mode": self.original_mode, "channels": self.channels, "warnings": self.warnings,
        }


def sniff_format(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if content.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if content[:4] in (b"II*\x00", b"MM\x00*"):
        return "TIFF"
    return None


def validate_upload(content: bytes, filename: str) -> ValidatedImage:
    if not content:
        raise ApiError(400, "empty_file", "The uploaded file is empty.")
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    if ext not in EXT_FORMAT:
        raise ApiError(400, "unsupported_extension", "Upload PNG, JPG, or TIFF")
    actual = sniff_format(content)
    if actual is None:
        raise ApiError(422, "invalid_image", "The file is not a readable PNG, JPEG or TIFF image (unusual multi-band TIFFs are not supported).")
    if actual != EXT_FORMAT[ext]:
        raise ApiError(415, "extension_mismatch", f"The file content is {actual} but its extension says .{ext}.")

    if actual == "TIFF":
        try:
            import rasterio
            from rasterio.io import MemoryFile

            with MemoryFile(content) as memfile:
                with memfile.open() as src:
                    # Check if this is a multi-band satellite raster (e.g. 2+ bands with non-8bit, or 6-band SAR, or non-RGB/non-CMYK 2-band)
                    is_cmyk = (
                        getattr(src, "photometric", None) == "CMYK"
                        or getattr(src, "profile", {}).get("photometric") == "CMYK"
                        or getattr(src, "colorinterp", None) and any("cmyk" in str(c).lower() for c in src.colorinterp)
                    )
                    is_satellite = (
                        not is_cmyk
                        and (
                            src.dtypes[0] in ("int16", "uint16", "int32", "uint32", "float32", "float64")
                            or src.count == 2
                            or src.count >= 5
                        )
                        and src.count >= 2
                    )

                    if is_satellite:
                        w, h = src.width, src.height
                        if w * h > settings.max_image_pixels:
                            raise ApiError(413, "image_too_large", f"Image is {w}x{h} px; the limit is {settings.max_image_pixels:,} pixels.")
                        if min(w, h) < MIN_SIDE:
                            raise ApiError(422, "image_too_small", f"Image is {w}x{h} px; each side must be at least {MIN_SIDE} px.")

                        b1 = src.read(1)
                        b2 = src.read(2)

                        def _norm(band):
                            band = band.astype(np.float32, copy=False)
                            valid = np.isfinite(band) & (band < 30000)
                            if not valid.any():
                                return np.zeros_like(band, dtype=np.float32)
                            values = band[valid]
                            low, high = np.percentile(values, [2, 98])
                            if not np.isfinite(low) or not np.isfinite(high) or high <= low:
                                low = float(values.min())
                                high = float(values.max())
                            if high <= low:
                                res = np.zeros_like(band, dtype=np.float32)
                            else:
                                safe = np.where(valid, band, low)
                                res = (np.clip(safe, low, high) - low) / (high - low)
                            res[~valid] = 0.0
                            return res.astype(np.float32, copy=False)

                        n1 = _norm(b1)
                        n2 = _norm(b2)
                        raw = np.stack([n1, n2], axis=-1)
                        rgb = np.stack([np.clip(n1 * 255.0, 0, 255), np.clip(n2 * 255.0, 0, 255), np.zeros_like(n1)], axis=-1).astype(np.uint8)
                        preview_img = Image.fromarray(rgb, mode="RGB")
                        warns = []
                        if src.count > 2:
                            warns.append(f"Multi-band satellite raster ({src.count} bands): bands 1 and 2 extracted.")
                        return ValidatedImage(preview_img, actual, f"multispectral_{src.count}band", warns, raw)
        except ApiError:
            raise
        except Exception:
            pass

    try:
        img = Image.open(io.BytesIO(content))
    except (OSError, ValueError, Image.DecompressionBombError):  # UnidentifiedImageError is an OSError
        raise ApiError(422, "invalid_image", "The file is not a readable PNG, JPEG or TIFF image (unusual multi-band TIFFs are not supported).")

    w, h = img.size
    if w * h > settings.max_image_pixels:
        raise ApiError(413, "image_too_large", f"Image is {w}x{h} px; the limit is {settings.max_image_pixels:,} pixels.")
    if min(w, h) < MIN_SIDE:
        raise ApiError(422, "image_too_small", f"Image is {w}x{h} px; each side must be at least {MIN_SIDE} px.")
    original_mode = img.mode
    if original_mode not in ("RGB", "RGBA", "L", "LA", "P"):
        raise ApiError(422, "unsupported_image_mode", f"Image mode '{original_mode}' is not supported. Use 8-bit RGB or grayscale (16-bit, float, CMYK and multi-band rasters are not supported).")

    warnings: list[str] = []
    if getattr(img, "n_frames", 1) > 1:
        warnings.append("Multi-frame image: only the first frame was analysed.")
    try:
        img.load()
    except (OSError, SyntaxError, ValueError):
        raise ApiError(422, "invalid_image", "The image data is corrupt or truncated.")

    if original_mode in ("RGBA", "LA"):
        warnings.append("Alpha channel was discarded.")
    if original_mode in ("RGBA", "P"):
        img = img.convert("RGB")
    elif original_mode == "LA":
        img = img.convert("L")
    return ValidatedImage(img, actual, original_mode, warnings)


def to_array(img: Image.Image) -> np.ndarray:
    """uint8 array (H, W, C) with C = 1 for grayscale, 3 for RGB."""
    arr = np.asarray(img, dtype=np.uint8)
    return arr[..., None] if arr.ndim == 2 else arr


def overlay_mask(img: Image.Image, mask: np.ndarray, max_px: int) -> Image.Image:
    """Blend a translucent colour over flooded pixels; downscale (never upscale) to max_px on the long side."""
    base = np.asarray(img.convert("RGB"), dtype=np.float32)
    colour = np.array(OVERLAY_COLOR, dtype=np.float32)
    blended = np.where(mask[..., None], base * (1 - OVERLAY_ALPHA) + colour * OVERLAY_ALPHA, base)
    out = Image.fromarray(np.rint(blended).astype(np.uint8))
    out.thumbnail((max_px, max_px))
    return out


def png_base64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def mask_image(mask: np.ndarray) -> Image.Image:
    return Image.fromarray(mask.astype(np.uint8) * 255)
