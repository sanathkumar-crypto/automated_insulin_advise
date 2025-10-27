# Deployment Guide

## Overview

This directory contains deployment configuration for deploying the Insulin Recommendation System as a microservice on Google Cloud Platform (GCP) Cloud Run.

## Prerequisites

1. **Google Cloud SDK** installed and configured
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

2. **Authentication**
   ```bash
   gcloud auth login
   gcloud config set project patientview-9uxml
   ```

3. **Required GCP APIs** (will be enabled automatically by the script)
   - Cloud Build API
   - Cloud Run API
   - Container Registry API

## Configuration

1. **Create .env file** in the project root:
   ```bash
   cd /Users/drdileepunni/github_/automated_insulin_advise
   cp .env.example .env
   ```

2. **Verify settings** in `.env`:
   ```bash
   PROJECT_ID=patientview-9uxml
   REGION=asia-south1
   SERVICE_NAME=insulin-recommendation
   ```

## Deployment

### Production Deployment

```bash
# From project root directory
./deployment/deploy-prod.sh
```

The script will:
1. ✅ Validate configuration
2. ✅ Check gcloud authentication
3. ✅ Enable required GCP APIs
4. ✅ Build Docker image using Cloud Build
5. ✅ Push image to Google Container Registry
6. ✅ Deploy to Cloud Run
7. ✅ Test health endpoint
8. ✅ Display service URL

### Manual Deployment (alternative)

If you prefer to deploy manually:

```bash
# Build and submit to Cloud Build
gcloud builds submit \
    --config deployment/cloudbuild.yaml \
    --substitutions=_REGION="asia-south1" \
    --project patientview-9uxml
```

## Service Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **Memory** | 512Mi | Sufficient for Python Flask app |
| **CPU** | 1 | Single CPU core |
| **Min Instances** | 0 | Scales to zero when idle |
| **Max Instances** | 10 | Auto-scales up to 10 instances |
| **Port** | 8080 | Container port |
| **Authentication** | Public | No authentication required |
| **Timeout** | 300s | Request timeout (default) |

## Service URLs

After deployment, your service will be available at:

```
https://insulin-recommendation-<hash>-as.a.run.app
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check & service info |
| `/recommend` | POST | Get insulin recommendation |

## Testing the Deployed Service

### Health Check

```bash
curl https://insulin-recommendation-<your-url>.a.run.app/
```

### Example API Call

```bash
curl -X POST https://insulin-recommendation-<your-url>.a.run.app/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "GRBS": [180, 200, 190, 185, 175],
    "Insulin": [2, 3, 2.5, 2, 1.5],
    "CKD": false,
    "Dual inotropes": false,
    "route": "sc",
    "diet_order": "NPO"
  }'
```

Expected response:
```json
{
  "Suggested_insulin_dose": 4,
  "Suggested_route": "subcutaneous",
  "next_grbs_after": 4,
  "algorithm_used": "Basal Bolus",
  "level": 3,
  "action": "Medium dose",
  "unit": "IU"
}
```

## Monitoring

### View Logs

```bash
# Stream logs
gcloud run services logs read insulin-recommendation \
    --region=asia-south1 \
    --project=patientview-9uxml \
    --tail

# View logs in Cloud Console
https://console.cloud.google.com/run/detail/asia-south1/insulin-recommendation/logs
```

### View Metrics

```bash
# Open Cloud Console metrics
https://console.cloud.google.com/run/detail/asia-south1/insulin-recommendation/metrics
```

## Updating the Service

To update the service with new code:

```bash
# Pull latest code
git pull origin main

# Run deployment script
./deployment/deploy-prod.sh
```

The deployment is zero-downtime - Cloud Run automatically handles traffic migration.

## Rollback

If you need to rollback to a previous version:

```bash
# List revisions
gcloud run revisions list \
    --service=insulin-recommendation \
    --region=asia-south1 \
    --project=patientview-9uxml

# Route traffic to previous revision
gcloud run services update-traffic insulin-recommendation \
    --to-revisions=<REVISION-NAME>=100 \
    --region=asia-south1 \
    --project=patientview-9uxml
```

## Cost Optimization

The service is configured for cost efficiency:

- **Scales to zero**: No charges when idle
- **512Mi memory**: Minimal resource allocation
- **Request-based billing**: Only pay for actual requests
- **Auto-scaling**: Scales up only when needed

Estimated cost: **~$0-5/month** for typical usage

## Troubleshooting

### Build Fails

```bash
# Check Cloud Build logs
gcloud builds list --project=patientview-9uxml --limit=5
gcloud builds log <BUILD-ID> --project=patientview-9uxml
```

### Service Not Responding

```bash
# Check service status
gcloud run services describe insulin-recommendation \
    --region=asia-south1 \
    --project=patientview-9uxml

# View recent logs
gcloud run services logs read insulin-recommendation \
    --region=asia-south1 \
    --project=patientview-9uxml \
    --limit=50
```

### Permission Errors

Ensure your account has the following IAM roles:
- Cloud Run Admin
- Cloud Build Editor
- Storage Admin (for Container Registry)

```bash
# Check current permissions
gcloud projects get-iam-policy patientview-9uxml \
    --flatten="bindings[].members" \
    --filter="bindings.members:$(gcloud config get-value account)"
```

## Security

### Public Access

This service is intentionally public because:
- No patient data is processed
- No sensitive information in requests/responses
- Pure algorithm-based calculations
- Stateless API design

### Best Practices Implemented

✅ Non-root user in Docker container  
✅ Minimal base image (python:3.12-slim)  
✅ Health checks configured  
✅ Resource limits set  
✅ Auto-scaling enabled  
✅ Request timeouts configured  

## Files

```
deployment/
├── Dockerfile           # Container image definition
├── cloudbuild.yaml      # Cloud Build configuration
├── deploy-prod.sh       # Deployment script
└── README.md           # This file
```

## Support

For issues or questions:
1. Check service logs
2. Review Cloud Build logs
3. Verify GCP quotas and limits
4. Contact DevOps team

---

**Last Updated**: Version 1.2.0

