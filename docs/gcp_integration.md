# Gemini / Vertex AI Integration

This document describes how to enable real Gemini/Vertex AI integration for `GeminiClient`.

Local development
1. Create a service account JSON with the `Vertex AI` permissions and save it locally.
2. Set one of these environment patterns (preferred):

Option A (file path):

```
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
export GEMINI_MODEL=projects/your-project/locations/us-central1/models/your-model
```

Option B (CI-friendly, inject JSON via secret):

Set `GOOGLE_SERVICE_ACCOUNT_JSON` to the full JSON service account string (as a secret). The app will write it to `gcp_service_account.json` and set `GOOGLE_APPLICATION_CREDENTIALS` automatically.

CI / GitHub Actions
1. Store the service account JSON as a repository secret `GCP_SA_JSON`.
2. In your workflow, write the secret to a file and set `GOOGLE_APPLICATION_CREDENTIALS`:

```yaml
- name: Write GCP service account
  run: |
    echo "$GCP_SA_JSON" > $GITHUB_WORKSPACE/gcp_sa.json
    echo "GOOGLE_APPLICATION_CREDENTIALS=$GITHUB_WORKSPACE/gcp_sa.json" >> $GITHUB_ENV
  env:
    GCP_SA_JSON: ${{ secrets.GCP_SA_JSON }}

- name: Set GCP project
  run: echo "GOOGLE_CLOUD_PROJECT=your-project-id" >> $GITHUB_ENV

- name: Install deps
  run: pip install -r requirements.txt

- name: Run tests / build
  run: pytest
```

Notes
- The code includes `backend/tools/setup_gcp_creds.py` to support `GOOGLE_SERVICE_ACCOUNT_JSON`.
- Add `google-cloud-aiplatform` to your environment (it's in `requirements.txt`).
- The `GeminiClient` will still fall back to the local planner/synthesizer if SDK calls fail or credentials/model are missing.
