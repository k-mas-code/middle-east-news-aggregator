# Deployment Guide

Complete guide for deploying the Middle East News Aggregator to Google Cloud Platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Google Cloud Platform                    │
│                                                               │
│  ┌──────────────────┐         ┌─────────────────────────┐   │
│  │  Cloud Run       │         │  Firebase Hosting       │   │
│  │  (FastAPI)       │◄────────│  (React Frontend)       │   │
│  │  Port 8080       │         │                         │   │
│  └────────┬─────────┘         └─────────────────────────┘   │
│           │                                                   │
│           ▼                                                   │
│  ┌──────────────────┐         ┌─────────────────────────┐   │
│  │  Firestore       │         │  Cloud Storage          │   │
│  │  (Database)      │         │  (Logs)                 │   │
│  └──────────────────┘         └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         ▲
         │
         │ (6 hours interval)
         │
    ┌────┴─────┐
    │  GitHub  │
    │  Actions │
    └──────────┘
```

## Prerequisites

- Google Cloud Platform account with billing enabled
- Firebase project (created from GCP Console)
- GitHub repository with appropriate secrets
- Firebase CLI installed locally
- gcloud CLI installed locally

## Step 1: GCP Project Setup

### 1.1 Create GCP Project

```bash
# Set your project ID
export PROJECT_ID="middle-east-news-aggregator"

# Create project
gcloud projects create $PROJECT_ID

# Set as default project
gcloud config set project $PROJECT_ID

# Link billing account (replace with your billing account ID)
gcloud beta billing projects link $PROJECT_ID \
  --billing-account=YOUR_BILLING_ACCOUNT_ID
```

### 1.2 Enable Required APIs

```bash
# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  firestore.googleapis.com \
  firebase.googleapis.com \
  storage.googleapis.com
```

### 1.3 Create Firestore Database

```bash
# Create Firestore database in native mode
gcloud firestore databases create \
  --region=asia-northeast1 \
  --type=firestore-native
```

## Step 2: Service Account Setup

### 2.1 Create Service Accounts

```bash
# Service account for GitHub Actions
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account"

# Service account for Cloud Run
gcloud iam service-accounts create cloud-run-sa \
  --display-name="Cloud Run Service Account"
```

### 2.2 Grant Permissions

```bash
# GitHub Actions permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.editor"

# Cloud Run permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"
```

### 2.3 Create Service Account Keys

```bash
# Create key for GitHub Actions
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Display key content (for GitHub Secrets)
cat github-actions-key.json

# IMPORTANT: Delete the key file after copying to GitHub
rm github-actions-key.json
```

## Step 3: Firebase Setup

### 3.1 Initialize Firebase

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Add Firebase to your GCP project
firebase projects:addfirebase $PROJECT_ID

# Initialize Firebase in your project
firebase init hosting

# When prompted:
# - Select: Use an existing project
# - Choose: middle-east-news-aggregator
# - Public directory: frontend/dist
# - Configure as SPA: Yes
# - Set up automatic builds: No
```

### 3.2 Create Firebase Service Account

```bash
# Create service account for Firebase Hosting
gcloud iam service-accounts create firebase-hosting-sa \
  --display-name="Firebase Hosting Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:firebase-hosting-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/firebasehosting.admin"

# Create key
gcloud iam service-accounts keys create firebase-hosting-key.json \
  --iam-account=firebase-hosting-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Display key content
cat firebase-hosting-key.json

# Delete after copying
rm firebase-hosting-key.json
```

## Step 4: GitHub Secrets Configuration

Add the following secrets to your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value | Source |
|-------------|-------|--------|
| `GCP_PROJECT_ID` | Your GCP project ID | `middle-east-news-aggregator` |
| `GCP_SA_KEY` | GitHub Actions service account JSON | Content of `github-actions-key.json` |
| `FIREBASE_SERVICE_ACCOUNT` | Firebase Hosting service account JSON | Content of `firebase-hosting-key.json` |

## Step 5: Local Testing

### 5.1 Test Backend Locally

```bash
# Build Docker image
docker build -t middle-east-aggregator .

# Run locally
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
  middle-east-aggregator

# Test API
curl http://localhost:8080/api/status
```

### 5.2 Test Frontend Locally

```bash
cd frontend

# Set API URL
echo "VITE_API_BASE_URL=http://localhost:8080" > .env.local

# Install and build
npm install
npm run build

# Preview
npm run preview
```

## Step 6: Manual Deployment

### 6.1 Deploy Backend to Cloud Run

```bash
# Build and submit to Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Or deploy directly
gcloud run deploy middle-east-aggregator \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi
```

### 6.2 Deploy Frontend to Firebase Hosting

```bash
cd frontend

# Build with production API URL
export VITE_API_BASE_URL=$(gcloud run services describe middle-east-aggregator \
  --region us-central1 \
  --format 'value(status.url)')

npm run build

# Deploy
cd ..
firebase deploy --only hosting
```

## Step 7: Continuous Deployment

### 7.1 Enable Automatic Deployment

Continuous deployment is configured via GitHub Actions:

- **Trigger:** Push to `main` or `master` branch
- **Workflow:** `.github/workflows/deploy.yml`

### 7.2 Manual Deployment Trigger

Go to GitHub Actions → Deploy to Cloud Run and Firebase Hosting → Run workflow

## Step 8: Monitoring and Maintenance

### 8.1 View Logs

```bash
# Cloud Run logs
gcloud run services logs read middle-east-aggregator \
  --region us-central1

# Cloud Build logs
gcloud builds list --limit 10
```

### 8.2 Monitor Costs

```bash
# View billing
gcloud beta billing accounts list
gcloud beta billing projects describe $PROJECT_ID
```

### 8.3 Check Service Status

```bash
# Cloud Run status
gcloud run services describe middle-east-aggregator \
  --region us-central1

# Firestore status
gcloud firestore operations list
```

## Cost Estimates (Free Tier)

| Service | Free Tier | Expected Usage | Cost |
|---------|-----------|----------------|------|
| Cloud Run | 2M requests/month | ~50K/month | $0 |
| Firestore | 1GB, 50K reads/day | ~500MB, 10K/day | $0 |
| Firebase Hosting | 10GB/month transfer | ~2GB/month | $0 |
| Cloud Build | 120 build-minutes/day | ~10 min/day | $0 |
| Cloud Storage | 5GB | ~1GB | $0 |

**Total monthly cost: $0** (within free tier limits)

## Troubleshooting

### Backend not accessible
```bash
# Check service status
gcloud run services list

# Check logs
gcloud run services logs read middle-east-aggregator --region us-central1
```

### Frontend build fails
```bash
# Check API URL is set
echo $VITE_API_BASE_URL

# Rebuild
cd frontend && npm run build
```

### Firestore permissions error
```bash
# Verify service account has datastore.user role
gcloud projects get-iam-policy $PROJECT_ID
```

### GitHub Actions deployment fails
- Verify all secrets are set correctly
- Check service account has required permissions
- Review GitHub Actions logs

## Security Best Practices

1. **Never commit service account keys to git**
2. **Use minimal required permissions**
3. **Rotate service account keys every 90 days**
4. **Enable GCP audit logs**
5. **Review GitHub Actions logs regularly**
6. **Set up billing alerts**
7. **Use Cloud Armor for DDoS protection (if needed)**

## Support

For issues:
- Check logs: `gcloud run services logs read middle-east-aggregator`
- Review GitHub Actions workflow runs
- Consult [GCP documentation](https://cloud.google.com/run/docs)
- Review [Firebase Hosting docs](https://firebase.google.com/docs/hosting)
