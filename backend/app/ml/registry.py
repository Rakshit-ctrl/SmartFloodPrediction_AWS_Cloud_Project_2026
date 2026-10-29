"""Model discovery and loading.

Looks for MODEL_DIR/model.json. Only a successfully loaded model is cached; any other state is
re-checked on the next call, so adding weights does not require a code change.
"""
import hashlib
import logging
import threading
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import ValidationError

from ..config import settings
from .base import ModelMeta, SegmentationModel

logger = logging.getLogger(__name__)
META_FILENAME = "model.json"


@dataclass(frozen=True)
class ModelStatus:
    state: str  # ready | not_configured | invalid_metadata | weights_missing | runtime_missing | load_failed
    message: str
    name: str | None = None
    version: str | None = None
    architecture: str | None = None
    weights_sha256: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


_lock = threading.Lock()
_loaded: tuple[SegmentationModel, ModelStatus] | None = None


def reset() -> None:
    global _loaded
    with _lock:
        _loaded = None


def _short(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'json'}: {e['msg']}" for e in exc.errors()[:3])
    return str(exc)[:200]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _try_load() -> tuple[SegmentationModel | None, ModelStatus]:
    model_dir = Path(settings.model_dir)
    meta_path = model_dir / META_FILENAME
    if not meta_path.is_file():
        return None, ModelStatus(
            "not_configured",
            f"No {META_FILENAME} in the model directory. No trained model is installed; see docs/MODEL_INTEGRATION.md.",
        )
    try:
        meta = ModelMeta.model_validate_json(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # pydantic's ValidationError is a ValueError
        return None, ModelStatus("invalid_metadata", f"{META_FILENAME} is invalid: {_short(exc)}")

    ident = dict(name=meta.name, version=meta.version, architecture=meta.architecture)
    weights = model_dir / meta.weights_file
    if not weights.is_file():
        return None, ModelStatus("weights_missing", f"Weights file '{meta.weights_file}' not found in the model directory.", **ident)
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return None, ModelStatus("runtime_missing", "onnxruntime is not installed. Run: pip install -r requirements-ml.txt", **ident)
    try:
        from .onnx_model import OnnxSegmentationModel

        model = OnnxSegmentationModel(meta, weights)
        digest = _sha256(weights)
    except Exception as exc:
        logger.exception("Model load failed")
        return None, ModelStatus("load_failed", f"Could not load the model ({type(exc).__name__}): {str(exc)[:200]}", **ident)
    return model, ModelStatus("ready", "Model loaded.", weights_sha256=digest, **ident)


def get_model() -> tuple[SegmentationModel | None, ModelStatus]:
    global _loaded
    with _lock:
        if _loaded is not None:
            return _loaded
        model, status = _try_load()
        if model is not None:
            _loaded = (model, status)
        return model, status
