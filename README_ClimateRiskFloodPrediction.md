# Climate Risk and Smart Flood Prediction

React/Vite + FastAPI + SQLite/MySQL application with OpenWeather atmospheric integration, demo risk assessments, dry-run alert rules, and satellite water/flood extent segmentation powered by ONNX Runtime.

> ### ⚠️ Important Scientific Distinctions
> - **Water / Flood Extent Segmentation**: Identifies surface water and flooded pixels from satellite imagery (SAR Bands 1 & 2 at acquisition time). It reflects observed surface water conditions when the satellite captured the image, **not** a forecast of future floods.
> - **Risk Assessment**: An illustrative demo heuristic (`demo_heuristic_v1`, `validated: false`) based on user-entered rainfall and river levels.
> - **Future Flood Forecasting**: Not currently implemented. This application is an educational prototype and research baseline; do not use it for life-safety or emergency management decisions.

---

## Architecture & Technology Stack

| Component | Technology | Role & Configuration |
|---|---|---|
| **Frontend** | React 19, Vite, Lucide Icons, Recharts | Accessible UI, live weather, risk creation, GeoTIFF upload & overlay visualization |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2 | Async REST API, file upload validation, model orchestration, database transactions |
| **Database** | SQLite (dev) / MySQL (prod) | Relational persistence for risk assessments, alert rules, and satellite run metadata |
| **ML Engine** | ONNX Runtime (CPU) | Multi-band SAR U-Net segmentation (`unet_sar2.onnx`, ~495 KB, ~110 ms CPU latency) |
| **Geospatial & Imaging** | Rasterio, NumPy, Pillow | In-memory 16-bit GeoTIFF decoding, 2nd–98th percentile SAR normalization, false-color previews |
| **Deployment** | Docker, ECS Fargate / App Runner | Lightweight container execution; **Amazon SageMaker is explicitly excluded** |

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 20+ (Node 22 recommended)

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements-dev-full.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```
- API Documentation (Swagger): `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/health`

### 2. Frontend Setup
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
- Open `http://localhost:5173` in your browser.

---

## Docker & Containerized Deployment

Run both the frontend and backend with a single command:
```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Container healthchecks monitor `/api/health` automatically.

---

## Verification & Automated Test Suites

### Backend Tests (102 tests passed)
```bash
cd backend
python -m pytest -v
```
Covers API endpoints, GeoTIFF geospatial calculations, Pillow/Rasterio image validation, ONNX Runtime session execution, repository integrity, risk heuristics, alert rules, and weather error handling.

### Frontend Tests (50 tests passed)
```bash
cd frontend
npm run test -- --run
npm run build
```
Covers component rendering, user interactions, axe accessibility audits (0 violations), WCAG color contrast, and production bundle generation.

---

## Machine Learning Model Details

- **Architecture**: Custom U-Net with 2-band SAR input (TIFF Bands 1 & 2), 8 base channels, batch normalization, and ReLU activations.
- **Normalization**: Per-tile 2nd–98th percentile clipping with invalid sentinel value handling ($\ge 30,000$).
- **Inference Runtime**: Exported to ONNX (opset 17, `unet_sar2.onnx`), running via ONNX Runtime CPU.
- **Validation**: Deterministic holdout (seed 42, 15% holdout = 244 tiles).
- **Holdout Performance**:
  - Operating Threshold: **0.50**
  - Pooled Dice Score: **0.5113**
  - Pooled IoU: **0.3435**
  - Precision: **0.5731**
  - Recall: **0.4616**
  - Inference Latency: **~110 ms** on Intel Core CPU.

See [`docs/MODEL_INTEGRATION.md`](file:///c:/Users/DELL/OneDrive/Desktop/ClimateRiskFloodPrediction/docs/MODEL_INTEGRATION.md) for full pipeline details.

---

## Cloud Deployment (AWS Target)

As detailed in [`docs/AWS_ARCHITECTURE.md`](file:///c:/Users/DELL/OneDrive/Desktop/ClimateRiskFloodPrediction/docs/AWS_ARCHITECTURE.md):
- **Frontend**: Hosted on AWS Amplify or Amazon S3 + CloudFront CDN.
- **Backend**: Containerized in Amazon ECS Fargate or AWS App Runner (spec templates in `deploy/aws/ecs-task-definition.json` and `deploy/aws/app-runner.yaml`).
- **No Amazon SageMaker**: SageMaker endpoints are explicitly excluded in favor of cost-effective, low-latency CPU container serving via ONNX Runtime.
- **Database**: Amazon RDS MySQL for multi-user production workloads.
- **Alert Notifications**: Amazon SNS with safety gates ensuring only scientifically validated scores trigger live broadcasts.
