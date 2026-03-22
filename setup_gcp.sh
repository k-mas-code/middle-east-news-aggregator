#!/bin/bash
# GCP project initialization script for Middle East News Aggregator
# This script sets up all required GCP services within free tier limits

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-middle-east-news-aggregator}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_ACCOUNT_NAME="news-aggregator-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "${GREEN}=== Middle East News Aggregator - GCP Setup ===${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Step 1: Create or select project
echo -e "${YELLOW}Step 1: Setting up GCP project${NC}"
if gcloud projects describe "$PROJECT_ID" &> /dev/null; then
    echo "Project $PROJECT_ID already exists"
else
    echo "Creating new project: $PROJECT_ID"
    gcloud projects create "$PROJECT_ID" --name="Middle East News Aggregator"
fi

gcloud config set project "$PROJECT_ID"
echo -e "${GREEN}✓ Project configured${NC}"
echo ""

# Step 2: Enable billing (user must do this manually if not already enabled)
echo -e "${YELLOW}Step 2: Checking billing${NC}"
if ! gcloud beta billing projects describe "$PROJECT_ID" &> /dev/null; then
    echo -e "${YELLOW}Warning: Billing is not enabled for this project${NC}"
    echo "Please enable billing at: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
    echo "Press Enter after enabling billing..."
    read -r
fi
echo -e "${GREEN}✓ Billing configured${NC}"
echo ""

# Step 3: Enable required APIs
echo -e "${YELLOW}Step 3: Enabling required APIs${NC}"
APIS=(
    "run.googleapis.com"              # Cloud Run
    "firestore.googleapis.com"        # Firestore
    "translate.googleapis.com"        # Cloud Translation API
    "cloudbuild.googleapis.com"       # Cloud Build (for Cloud Run deployment)
    "artifactregistry.googleapis.com" # Artifact Registry (for container images)
)

for api in "${APIS[@]}"; do
    echo "Enabling $api..."
    gcloud services enable "$api" --project="$PROJECT_ID"
done
echo -e "${GREEN}✓ APIs enabled${NC}"
echo ""

# Step 4: Create Firestore database
echo -e "${YELLOW}Step 4: Creating Firestore database${NC}"
if gcloud firestore databases describe --project="$PROJECT_ID" &> /dev/null; then
    echo "Firestore database already exists"
else
    echo "Creating Firestore database in Native mode..."
    gcloud firestore databases create --region="$REGION" --project="$PROJECT_ID"
fi
echo -e "${GREEN}✓ Firestore configured${NC}"
echo ""

# Step 5: Create service account
echo -e "${YELLOW}Step 5: Creating service account${NC}"
if gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" --project="$PROJECT_ID" &> /dev/null; then
    echo "Service account $SERVICE_ACCOUNT_EMAIL already exists"
else
    echo "Creating service account..."
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --display-name="News Aggregator Service Account" \
        --project="$PROJECT_ID"
fi

# Grant necessary roles
echo "Granting IAM roles..."
ROLES=(
    "roles/datastore.user"        # Firestore read/write
    "roles/cloudtranslate.user"   # Translation API
    "roles/run.admin"             # Cloud Run management
    "roles/iam.serviceAccountUser" # Service account usage
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
        --role="$role" \
        --quiet
done
echo -e "${GREEN}✓ Service account configured${NC}"
echo ""

# Step 6: Create and download service account key
echo -e "${YELLOW}Step 6: Creating service account key${NC}"
KEY_FILE="./gcp-key.json"
if [ -f "$KEY_FILE" ]; then
    echo "Key file $KEY_FILE already exists"
    echo "Skipping key creation (delete existing key if you want to regenerate)"
else
    echo "Creating new service account key..."
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="$SERVICE_ACCOUNT_EMAIL" \
        --project="$PROJECT_ID"

    # Set restrictive permissions on key file
    chmod 600 "$KEY_FILE"
    echo -e "${GREEN}✓ Key created: $KEY_FILE${NC}"
fi
echo ""

# Step 7: Display GitHub Secrets configuration
echo -e "${YELLOW}Step 7: GitHub Secrets Configuration${NC}"
echo "Add the following secrets to your GitHub repository:"
echo "Go to: https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions"
echo ""
echo -e "${GREEN}Secret: GCP_PROJECT_ID${NC}"
echo "$PROJECT_ID"
echo ""
echo -e "${GREEN}Secret: GCP_SA_KEY${NC}"
echo "Copy the entire contents of $KEY_FILE"
echo ""
echo -e "${GREEN}Secret: FIREBASE_SERVICE_ACCOUNT${NC}"
echo "Copy the entire contents of $KEY_FILE (same as GCP_SA_KEY)"
echo ""

# Step 8: Display environment variables for local development
echo -e "${YELLOW}Step 8: Local Development Configuration${NC}"
echo "Add these to your .env file:"
echo ""
cat > .env.example << EOF
# GCP Configuration
GCP_PROJECT_ID=$PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=./gcp-key.json

# Translation API Configuration
TRANSLATION_MODE=titles_and_summary
TRANSLATION_MONTHLY_LIMIT=500000
TRANSLATION_SAFE_MARGIN=0.80
TRANSLATION_DISABLE_THRESHOLD=0.95
TRANSLATION_DAILY_LIMIT=20000
TRANSLATION_MAX_PER_ARTICLE=5000

# Cloud Run Configuration
PORT=8080
EOF

echo "Created .env.example with default configuration"
echo ""

# Summary
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env"
echo "2. Add GitHub secrets (shown above)"
echo "3. Test locally: docker build . && docker run -p 8080:8080 ..."
echo "4. Deploy: git push origin main (triggers GitHub Actions)"
echo ""
echo -e "${YELLOW}Free Tier Monitoring:${NC}"
echo "- Google Translation API: 500K chars/month"
echo "- Firestore: 50K reads, 20K writes, 1GB storage per day"
echo "- Cloud Run: 2M requests, 360K GB-seconds per month"
echo ""
echo "Monitor usage at:"
echo "https://console.cloud.google.com/apis/dashboard?project=$PROJECT_ID"
echo ""
