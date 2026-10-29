from fastapi import APIRouter

from ..ml.registry import get_model

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/model", summary="Segmentation model status and metadata")
def model_status():
    model, status = get_model()
    out = status.as_dict()
    if model is not None:
        out["input"] = model.meta.input.model_dump()
        out["output"] = model.meta.output.model_dump()
        out["training_notes_unverified"] = model.meta.training
    return out
