# AWS Target Deployment Architecture (Phase E Plan)

> **Important Constraint**: Amazon SageMaker is **explicitly excluded** from this architecture. All inference is designed around lightweight CPU containerized execution (ECS Fargate or App Runner) running ONNX Runtime.

## High-Level Architecture Flow

```
[User Browser]
      │
      ▼ (HTTPS)
[AWS Amplify / S3 + CloudFront] (React + Vite Single-Page App)
      │
      ▼ (REST API / CORS)
[Amazon API Gateway / Application Load Balancer]
      │
      ▼
[Amazon ECS Fargate / AWS App Runner] (Containerized FastAPI + ONNX Runtime CPU)
   ├─── Model Weights & Image Artifacts ──────> [Amazon S3] (Encrypted, Private)
   ├─── Relational Data (Assessments, Rules) ─> [Amazon RDS MySQL 8.0]
   ├─── User Authentication & Roles ──────────> [Amazon Cognito]
   ├─── Alert Event Notifications ─────────────> [Amazon SNS] (Gate: validated=true only)
   └─── Health & Application Telemetry ────────> [Amazon CloudWatch]
```

## Detailed Service Roles

1. **Frontend Hosting**:
   - **Service**: AWS Amplify Hosting or Amazon S3 static website hosting fronted by Amazon CloudFront (CDN with SSL/TLS).
   - **Assets**: Output of `npm run build` (`dist/`).
2. **Backend API & ML Serving**:
   - **Service**: Amazon ECS Fargate (or AWS App Runner) running the unified FastAPI application in a Docker container.
   - **Why Container instead of raw Lambda**: Eliminates cold-start timeouts and package size limitations associated with GIS/geospatial libraries (`rasterio`, `GDAL`, `onnxruntime`, `torch`).
   - **Runtime**: Python 3.11 with ONNX Runtime (CPU execution provider). Since `unet_sar2.onnx` is only ~495 KB and takes ~110 ms on CPU, Fargate 0.5 vCPU / 1 GB RAM is sufficient and cost-effective.
   - **No SageMaker**: SageMaker endpoints are unnecessary, significantly more expensive, and explicitly excluded.
3. **Storage (Amazon S3)**:
   - S3 Bucket for raw uploaded satellite TIFFs, derived binary masks, and model checkpoints.
   - Presigned S3 URLs used for secure, time-limited direct client uploads if file sizes exceed API Gateway payload limits (10 MB).
4. **Relational Database (Amazon RDS MySQL)**:
   - Replaces local SQLite `flood_app.db` for multi-user transactional integrity.
   - Stores `risk_assessments`, `alerts`, `alert_events`, and `satellite_analyses`.
   - Schema managed via Alembic migrations.
5. **Alert Notifications (Amazon SNS)**:
   - Evaluates triggered alert rules.
   - Safety gate: Refuses to dispatch SMS/Email notifications if `validated` is `false` (demo scores can never trigger real emergency alerts).
6. **Observability & Security**:
   - AWS Secrets Manager / Parameter Store for database credentials and `OPENWEATHER_API_KEY`.
   - Amazon CloudWatch for structured access logging, latency metrics, and error alarms.
   - IAM least-privilege roles for container execution.
