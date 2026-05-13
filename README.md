# RSCommendation Backend

FastAPI recommendation backend for Radboud Sport & Culture.

See `AGENTS.md` for full architecture, Firestore schema, and local dev commands.

---

## Deploying to GCP (Cloud Run)

Deployment is manual: go to the **Actions** tab in GitHub → **Manual Deploy** → **Run workflow**.

The workflow builds the Docker image, pushes it to Artifact Registry, and deploys it to Cloud Run in `europe-west4`.

### One-time GCP bootstrap

Run these commands once from a terminal with `gcloud` authenticated as a project owner.

#### 1. Enable required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project=rscommendation-493408
```

#### 2. Create the Artifact Registry repository

```bash
gcloud artifacts repositories create backend \
  --repository-format=docker \
  --location=europe-west4 \
  --project=rscommendation-493408
```

#### 3. Create the service account

```bash
gcloud iam service-accounts create rscommendation-api \
  --display-name="RSCommendation API" \
  --project=rscommendation-493408
```

#### 4. Grant the service account the required roles

```bash
# Read/write Firestore
gcloud projects add-iam-policy-binding rscommendation-493408 \
  --member="serviceAccount:rscommendation-api@rscommendation-493408.iam.gserviceaccount.com" \
  --role="roles/datastore.user"

# Deploy and manage Cloud Run services
gcloud projects add-iam-policy-binding rscommendation-493408 \
  --member="serviceAccount:rscommendation-api@rscommendation-493408.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Push images to Artifact Registry
gcloud projects add-iam-policy-binding rscommendation-493408 \
  --member="serviceAccount:rscommendation-api@rscommendation-493408.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Allow the SA to act as itself during Cloud Run deployment
gcloud iam service-accounts add-iam-policy-binding \
  rscommendation-api@rscommendation-493408.iam.gserviceaccount.com \
  --member="serviceAccount:rscommendation-api@rscommendation-493408.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser" \
  --project=rscommendation-493408
```

#### 5. Set up Workload Identity Federation for GitHub Actions

This allows GitHub Actions to authenticate to GCP without storing a service account JSON key.

```bash
# Create the Workload Identity pool
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool" \
  --project=rscommendation-493408

# Create the OIDC provider inside the pool
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --workload-identity-pool=github-pool \
  --location=global \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor" \
  --attribute-condition="assertion.repository=='<YOUR_GITHUB_ORG_OR_USER>/rscommendation-backend'" \
  --project=rscommendation-493408
```

Replace `<YOUR_GITHUB_ORG_OR_USER>` with your GitHub organisation or username.

#### 6. Bind the service account to the Workload Identity pool

```bash
# Get the pool's full resource name
WIF_POOL=$(gcloud iam workload-identity-pools describe github-pool \
  --location=global \
  --project=rscommendation-493408 \
  --format="value(name)")

# Allow tokens from your GitHub repo to impersonate the SA
gcloud iam service-accounts add-iam-policy-binding \
  rscommendation-api@rscommendation-493408.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WIF_POOL}/attribute.repository/<YOUR_GITHUB_ORG_OR_USER>/rscommendation-backend" \
  --project=rscommendation-493408
```

#### 7. Add GitHub Actions secrets

Add the following two secrets to the GitHub repository (Settings → Secrets and variables → Actions):

| Secret name | Value |
|---|---|
| `WIF_PROVIDER` | Output of: `gcloud iam workload-identity-pools providers describe github-provider --workload-identity-pool=github-pool --location=global --project=rscommendation-493408 --format="value(name)"` |
| `WIF_SERVICE_ACCOUNT` | `rscommendation-api@rscommendation-493408.iam.gserviceaccount.com` |

---

## Local development

See `AGENTS.md` for full instructions. Quick start:

```bash
# With Docker (preferred)
docker compose up

# Without Docker
uvicorn main:app --reload --port 8000
```

Requires a `.env` file at the repo root and GCP Application Default Credentials.
See `.env.example` for the required variables.
