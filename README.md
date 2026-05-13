# RSCommendation Backend

FastAPI recommendation backend for Radboud Sport & Culture.

See `AGENTS.md` for full architecture, Firestore schema, and local dev commands.

---

## Deploying to GCP (Cloud Run)

Deployment is manual: go to the **Actions** tab in GitHub → **Manual Deploy** → **Run workflow**.

The workflow builds the Docker image, pushes it to Artifact Registry, and deploys it to Cloud Run in `europe-west4`.

### GitHub Actions secrets

The following secrets must be set in the repository (Settings → Secrets and variables → Actions):

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
