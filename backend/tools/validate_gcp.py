import os
import json
import sys

def main():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    model = os.getenv("GEMINI_MODEL")
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    print("GCP Validation: checking environment variables...")
    print(f"GOOGLE_CLOUD_PROJECT={project}")
    print(f"GEMINI_MODEL={model}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS={creds}")

    try:
        import google.cloud.aiplatform as aiplatform  # type: ignore
        print("google-cloud-aiplatform is installed")
    except Exception as e:
        print("google-cloud-aiplatform not installed:", e)
        print("If you plan to use Gemini/Vertex, install: pip install google-cloud-aiplatform")
        return 2

    # Try to initialize aiplatform
    try:
        aiplatform.init(project=project)
        print("aiplatform initialized")
    except Exception as e:
        print("aiplatform init failed:", e)

    if model:
        try:
            from google.cloud.aiplatform import TextGenerationModel  # type: ignore
            print("TextGenerationModel class available")
            try:
                model_obj = TextGenerationModel.from_pretrained(model)
                print("Loaded model object (no network call performed by this check if cached)")
            except Exception as e:
                print("Failed to load model object (this may require network/GCP access):", e)
        except Exception as e:
            print("TextGenerationModel not available in installation:", e)

    # Check for service-account-in-env pattern
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        print("GOOGLE_SERVICE_ACCOUNT_JSON is set (will be written by setup_gcp_creds if used)")

    print("Validation complete.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
