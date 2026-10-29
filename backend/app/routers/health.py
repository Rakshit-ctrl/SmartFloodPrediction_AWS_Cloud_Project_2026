from fastapi import APIRouter

from ..ml.registry import get_model

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", summary="API liveness and model status")
def health():
    _, status = get_model()
    return {"status": "ok", "model_configured": status.state == "ready", "model_state": status.state}
