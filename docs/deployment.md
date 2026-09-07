# Deploying StudioOps to Google Cloud Run

Both services are containerized and run on Cloud Run. Credentials are supplied at
deploy time through **Secret Manager** — nothing sensitive lives in the images or
the repository.

There are two topologies:

- **Split origin (simplest):** frontend and backend are separate Cloud Run
  services. The browser calls the backend directly via `NEXT_PUBLIC_API_BASE_URL`.
- **Same origin:** the frontend service proxies `/api` and `/reports` to the
  backend via `BACKEND_ORIGIN`, so there is one public URL and no CORS.

This guide uses the split-origin setup and notes the same-origin variant at the
end.

---

## 0. Prerequisites

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable the APIs used here.
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com

export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1
```

Create an Artifact Registry repo for the images (once):

```bash
gcloud artifacts repositories create studioops \
  --repository-format=docker --location=$REGION
```

---

## 1. Store secrets in Secret Manager

Create the secrets. Values arrive at deploy time — you do **not** put them in the
repo or the image.

```bash
# Parallel Search API key
printf '%s' "YOUR_PARALLEL_API_KEY" | \
  gcloud secrets create PARALLEL_API_KEY --data-file=-

# Gemini via Vertex AI: the service-account JSON, stored whole.
gcloud secrets create GEMINI_SA_JSON --data-file=/path/to/service-account.json

# (Alternative to Vertex) Gemini Developer API key instead of a service account:
# printf '%s' "YOUR_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
```

Give the runtime service account access. Using the default compute SA here; a
dedicated SA is fine too.

```bash
export RUNTIME_SA="$(gcloud projects describe $PROJECT_ID \
  --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

for SECRET in PARALLEL_API_KEY GEMINI_SA_JSON; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:$RUNTIME_SA" \
    --role="roles/secretmanager.secretAccessor"
done

# Vertex AI access for the runtime SA.
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/aiplatform.user"
```

---

## 2. Build and push the backend image

Built from the repo root so the whole `backend/` package is in the build context.

```bash
export API_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/studioops/api:latest"

gcloud builds submit \
  --tag "$API_IMAGE" \
  --config=/dev/stdin <<'EOF'
steps:
  - name: gcr.io/cloud-builders/docker
    args: ['build','-f','backend/Dockerfile','-t','${_IMAGE}','.']
images: ['${_IMAGE}']
substitutions:
  _IMAGE: PLACEHOLDER
EOF
```

Or, more simply, with a local Docker daemon:

```bash
docker build -f backend/Dockerfile -t "$API_IMAGE" .
docker push "$API_IMAGE"
```

---

## 3. Deploy the backend service

The service-account JSON is mounted from Secret Manager as an environment
variable; the app's startup bootstrap (`setup_gcp_creds.py`) writes it to disk
and points `GOOGLE_APPLICATION_CREDENTIALS` at it automatically.

```bash
gcloud run deploy studioops-api \
  --image "$API_IMAGE" \
  --region $REGION \
  --service-account "$RUNTIME_SA" \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 --memory 1Gi \
  --timeout 300 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,GEMINI_MODEL=gemini-2.5-flash" \
  --set-secrets "PARALLEL_API_KEY=PARALLEL_API_KEY:latest,GOOGLE_SERVICE_ACCOUNT_JSON=GEMINI_SA_JSON:latest"
```

> Using the **Developer API** instead of Vertex? Drop the `GOOGLE_GENAI_*` and
> Vertex vars and set `--set-secrets "...,GEMINI_API_KEY=GEMINI_API_KEY:latest"`.

Capture the URL and verify:

```bash
export API_URL="$(gcloud run services describe studioops-api \
  --region $REGION --format='value(status.url)')"

curl "$API_URL/health"          # {"status":"ok"}
curl "$API_URL/api/v1/config"   # both integrations should report configured:true
```

`/api/v1/config` is the single source of truth for whether the live integrations
came up. If either reports `configured:false`, the secret binding is wrong —
check the service's env/secret wiring before deploying the frontend.

---

## 4. Build, push, and deploy the frontend

`NEXT_PUBLIC_API_BASE_URL` is baked in at **build time**, so pass the backend URL
as a build arg.

```bash
export WEB_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/studioops/web:latest"

docker build -f frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_API_BASE_URL="$API_URL" \
  -t "$WEB_IMAGE" ./frontend
docker push "$WEB_IMAGE"

gcloud run deploy studioops-web \
  --image "$WEB_IMAGE" \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 --memory 512Mi
```

Then lock CORS on the backend to the frontend origin:

```bash
export WEB_URL="$(gcloud run services describe studioops-web \
  --region $REGION --format='value(status.url)')"

gcloud run services update studioops-api --region $REGION \
  --update-env-vars "CORS_ALLOW_ORIGINS=$WEB_URL"
```

Open `$WEB_URL` and run a research brief end to end.

---

## Same-origin variant

If you prefer one public URL and no CORS, deploy the frontend **without**
`NEXT_PUBLIC_API_BASE_URL` and instead point it at the backend at runtime:

```bash
docker build -f frontend/Dockerfile -t "$WEB_IMAGE" ./frontend   # no build-arg
docker push "$WEB_IMAGE"

gcloud run deploy studioops-web \
  --image "$WEB_IMAGE" --region $REGION --allow-unauthenticated --port 8080 \
  --set-env-vars "BACKEND_ORIGIN=$API_URL"
```

With `NEXT_PUBLIC_API_BASE_URL` unset, `next.config.mjs` proxies `/api` and
`/reports` to `BACKEND_ORIGIN`, so the browser only ever talks to the frontend
origin and CORS is not needed.

---

## Notes and caveats

- **Reports are ephemeral.** The backend writes Markdown/JSON to the container's
  in-memory filesystem and streams it to the browser; on Cloud Run this does not
  persist across instances or restarts, which is fine for V1. For durable
  downloads, mount a GCS bucket (e.g. via Cloud Storage FUSE) at `outputs/`.
- **Single worker.** The run store and SSE pub/sub are in-process, so the backend
  runs one Uvicorn worker. Scale with Cloud Run instances, and set
  `--max-instances`/session affinity if long SSE streams must stick to one
  instance. For multi-instance durability, move the run store to Redis/Firestore.
- **Secret rotation.** Add a new secret version and redeploy (or reference
  `:latest`). Never bake a key into an image or commit it.
- **Startup logs** state which integrations came up
  (`integration.parallel ready`, `integration.gemini ready mode=... model=...`),
  so a misconfigured deploy is obvious in Cloud Logging.
