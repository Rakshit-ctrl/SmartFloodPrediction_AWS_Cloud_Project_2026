# Model integration

**Status: Trained U-Net SAR baseline model integrated (`backend/models_deployed/`).**
The model is loaded automatically when `MODEL_DIR` points to `models_deployed` or when running locally.
`GET /api/model` and `GET /api/health` report live status, architecture, and training notes.

## What segmentation means here
A segmentation model labels pixels of one uploaded image as flooded/water-like or not. It is **not** a
weather observation, **not** a risk score, and **not** a forecast of a future flood. Those are separate
features (see `docs/RISK_METHODOLOGY.md`).

## Request flow
`POST /api/satellite/analyze` -> size limit -> extension and content sniffing -> decode (pixel limit, minimum
size, supported modes) -> model lookup -> channel check -> preprocessing (percentile normalization for SAR rasters,
mean/std for RGB/grayscale) -> ONNX inference -> mask checks -> mask PNG + overlay PNG + flooded-pixel statistics ->
optional area estimate -> metadata saved to database (images and masks are never stored in the database).

## Integrated Model: `unet-sar2-baseline`
- **Architecture**: 4-stage U-Net (121,105 parameters).
- **Format**: Self-contained ONNX (`opset_version 17`).
- **Input**: 2 channels (Band 1 VV and Band 2 VH), 512×512 pixels.
- **Normalization**: Per-tile 2nd and 98th percentiles (`percentile_sar`). Sentinel values >= 30,000 excluded.
- **Output**: Binary logits converted to probabilities via Sigmoid, evaluated at optimal threshold `0.50`.
- **Holdout Performance**: Pooled Dice: **0.5113**, IoU: **0.3435**, Precision: **0.5731**, Recall: **0.4616** on the 244-tile holdout.
- **Inference Latency**: ~110 ms on CPU.

### `model.json`
```json
{
  "name": "unet-sar2-baseline",
  "version": "2026-10-28",
  "architecture": "U-Net",
  "format": "onnx",
  "weights_file": "unet_sar2.onnx",
  "input": {
    "width": 512,
    "height": 512,
    "channels": 2,
    "normalization": "percentile_sar",
    "mean": [0.0, 0.0],
    "std": [1.0, 1.0],
    "scale": 1.0
  },
  "output": {
    "type": "binary_logits",
    "threshold": 0.5
  },
  "training": {
    "task": "Water / flood extent segmentation (Track 1 baseline)",
    "bands": ["Band 1 (VV)", "Band 2 (VH)"],
    "best_epoch": 4,
    "holdout_dice_per_tile": 0.4391,
    "best_pooled_dice": 0.5113,
    "notes": "Water/flood extent segmentation baseline trained on Track 1 bands 1 and 2. Per-tile 2-98th percentile normalization. Sentinel values >= 30000 excluded. This model identifies surface water extent in satellite imagery; it is not a future flood forecasting model."
  }
}
```

| Field | Meaning |
|---|---|
| `input.width/height` | Expected spatial dimensions (512×512). Dynamic dimensions are scaled as necessary. |
| `input.channels` | `1`, `2`, or `3`. The upload must match the channel count expected by the model. |
| `input.normalization` | `percentile_sar` (applies per-tile 2nd/98th percentile normalization for SAR TIFFs) or `mean_std` (standard scale/mean/std per channel). |
| `output.type` | `binary_logits` (sigmoid applied), `binary_probabilities`, or `multiclass_logits` (argmax). |
| `output.threshold` | Probability threshold for binary outputs (0 to 1, default 0.5). |
| `weights_file` | File name only (no folder paths). |

## Supported imagery
1. **Multi-band & 16-bit GeoTIFF (Satellite)**: 16-bit `int16`/`uint16` or multi-band TIFFs (including IEEE GRSS Track 1 imagery). Bands 1 and 2 are automatically parsed and normalized for 2-channel models; a false-colour RGB composite (Red=Band 1, Green=Band 2, Blue=0) is rendered for dashboard visualization.
2. **Standard 8-bit Images**: 8-bit PNG, JPEG, or 8-bit TIFF with 1 channel (grayscale) or 3 channels (RGB) for models expecting 1 or 3 channels.
3. **Rejected with specific errors**: Corrupt files, non-satellite single-band 16-bit/float rasters, CMYK color profiles, images exceeding `MAX_IMAGE_PIXELS` (default 25 million) or under 32 px a side.

## Flood-area estimates
Reported only for GeoTIFF imagery with a **projected CRS** (linear units, converted to metres), a valid
transform, and the same size as the decoded image.
Area = flooded pixels × pixel area. Otherwise `area.available` is `false` with the reason (not a GeoTIFF,
no CRS, geographic degrees, rasterio missing). No coordinates or map locations are returned or invented.
The estimate inherits all model error and is not validated.

## Model states (`GET /api/model`)
| state | meaning |
|---|---|
| `ready` | Loaded; analyses produce masks. |
| `not_configured` | No `model.json` found. |
| `invalid_metadata` | `model.json` failed validation (reason shown). |
| `weights_missing` | `model.json` names a file that is not there. |
| `runtime_missing` | `onnxruntime` not installed. |
| `load_failed` | ONNX file could not be loaded or does not match `model.json`. |

Inference errors return HTTP 500 `inference_failed` with a generic message; details go to the server log.

## Trying the pipeline without real weights
`tools/make_synthetic_model.py` writes a **synthetic brightness detector** named
`synthetic-brightness-DEMO-NOT-A-FLOOD-MODEL` (it flags bright pixels, which includes clouds and snow).
Use it only to see masks and overlays work; never present its output as flood detection.
```powershell
cd backend
pip install -r requirements-dev-full.txt
python tools\make_synthetic_model.py --out models_demo
$env:MODEL_DIR = (Resolve-Path models_demo).Path
uvicorn app.main:app --reload
```

## Evaluation requirements (before any accuracy claim)
Use held-out data separated by flood event and geography (no tiles of one event in both train and test).
Report IoU, Dice, precision, recall, F1, inference latency and cost, and keep test data untouched during model
selection. This repository contains no evaluation results because it contains no trained model.

## Deployment note
`onnxruntime` on CPU is the baseline runtime. Whether a given model fits AWS Lambda (package size, memory,
duration) must be measured for that model; the AWS document will present an inference option accordingly
instead of assuming Lambda works.
