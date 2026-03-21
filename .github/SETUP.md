# GitHub Actions Setup Guide

This guide explains how to configure GitHub Secrets for automated news collection.

## Required Secrets

The following secrets must be configured in your GitHub repository:

### 1. `GCP_PROJECT_ID`

Your Google Cloud Platform project ID.

**To find your project ID:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project from the dropdown
3. Copy the Project ID (not the Project Name)

**Example:** `middle-east-news-aggregator`

### 2. `GCP_SA_KEY`

Service account JSON key for authentication.

**To create a service account key:**

1. **Create Service Account:**
   ```bash
   gcloud iam service-accounts create github-actions-sa \
     --display-name="GitHub Actions Service Account"
   ```

2. **Grant Required Roles:**
   ```bash
   PROJECT_ID="your-project-id"

   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
     --role="roles/datastore.user"
   ```

3. **Create and Download Key:**
   ```bash
   gcloud iam service-accounts keys create github-actions-key.json \
     --iam-account=github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com
   ```

4. **Copy the JSON key content:**
   ```bash
   cat github-actions-key.json
   ```

5. **Add to GitHub Secrets:**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `GCP_SA_KEY`
   - Value: Paste the entire JSON content
   - Click "Add secret"

6. **Delete the local key file (security):**
   ```bash
   rm github-actions-key.json
   ```

## Adding Secrets to GitHub

1. Navigate to your repository on GitHub
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:
   - **Name:** `GCP_PROJECT_ID`
   - **Value:** Your GCP project ID

   - **Name:** `GCP_SA_KEY`
   - **Value:** Your service account JSON key

## Workflow Schedule

The collection workflow runs automatically:
- **Schedule:** Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)
- **Manual trigger:** Available via "Actions" tab → "Scheduled News Collection" → "Run workflow"

## Verifying Setup

After configuring secrets:

1. Go to **Actions** tab in your repository
2. Select **Scheduled News Collection**
3. Click **Run workflow** → **Run workflow**
4. Wait for completion and check logs

**Expected output:**
```
==========================================
COLLECTION SUMMARY
==========================================
Status: SUCCESS
✓ Articles collected: 50
✓ Articles filtered: 15
✓ Clusters created: 5
✓ Reports generated: 5
✓ Duration: 45.2s
✓ Filter rate: 30.0%
==========================================
```

## Troubleshooting

### Error: "Failed to authenticate to Google Cloud"
- Verify `GCP_SA_KEY` is set correctly
- Ensure the JSON is valid (not truncated)
- Check service account has required roles

### Error: "Permission denied on Firestore"
- Grant `roles/datastore.user` role to service account
- Ensure Firestore API is enabled

### Workflow not running on schedule
- Check repository has recent commits (GitHub may disable workflows in inactive repos)
- Verify cron syntax in `.github/workflows/collect.yml`
- Enable workflows in Settings → Actions → General

## Cost Monitoring

This setup uses Google Cloud free tier:
- **GitHub Actions:** 2,000 minutes/month free
- **Firestore:** 1 GB storage, 50K reads/day free
- **Cloud Functions/Run:** Not used by scheduled collection

Monitor your usage at: https://console.cloud.google.com/billing

## Security Best Practices

1. **Never commit service account keys to git**
2. **Use minimal required permissions** (datastore.user only)
3. **Rotate service account keys** every 90 days
4. **Enable GCP audit logs** to monitor access
5. **Review workflow logs** for suspicious activity

## Support

For issues:
- Check workflow logs in Actions tab
- Review `collection.log` artifact if available
- Consult [tasks.md](../../tasks.md) for implementation details
