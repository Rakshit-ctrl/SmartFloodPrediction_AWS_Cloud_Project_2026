from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import SatelliteAnalysis
from ..schemas import SatelliteAnalysisOut
from ..services.satellite import analyze_image

router = APIRouter(prefix="/api", tags=["satellite"])


def _persist(db: Session, result: dict) -> None:
    area = result["area"]
    db.add(SatelliteAnalysis(
        filename=result["filename"],
        bytes_received=result["bytes_received"],
        width=result["image"]["width"],
        height=result["image"]["height"],
        model_name=result["model"]["name"],
        model_version=result["model"]["version"],
        weights_sha256=result["model"]["weights_sha256"],
        flooded_pixels=result["mask"]["flooded_pixels"],
        total_pixels=result["mask"]["total_pixels"],
        flooded_fraction=result["mask"]["flooded_fraction"],
        flooded_area_km2=area["flooded_area_km2"] if area["available"] else None,
        inference_ms=result["inference_ms"],
    ))
    db.commit()


@router.post("/satellite/analyze", summary="Validate a satellite image and run the configured segmentation model")
async def analyze(file: UploadFile = File(...), db: Session = Depends(get_db)):
    max_bytes = settings.upload_max_bytes
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, "File too large")
    result = await run_in_threadpool(analyze_image, content, file.filename or "")
    if result["status"] == "completed":
        await run_in_threadpool(_persist, db, result)
    return result


@router.get("/satellite/analyses", response_model=list[SatelliteAnalysisOut], summary="History of completed segmentation runs (metadata only)")
def list_analyses(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(SatelliteAnalysis).order_by(SatelliteAnalysis.id.desc()).limit(max(1, min(limit, 200))).all()
