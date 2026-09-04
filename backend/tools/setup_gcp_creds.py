import os
from pathlib import Path


def bootstrap_service_account_from_env():
    """If `GOOGLE_SERVICE_ACCOUNT_JSON` env var is set (full JSON string),
    write it to the path specified by `GOOGLE_APPLICATION_CREDENTIALS` or
    to a reasonable default and export that path.
    """
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        return None

    out_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not out_path:
        out_path = str(Path(os.getcwd()) / "gcp_service_account.json")

    try:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            f.write(sa_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = out_path
        return out_path
    except Exception:
        return None


if __name__ == "__main__":
    path = bootstrap_service_account_from_env()
    if path:
        print("Wrote service account to:", path)
    else:
        print("No GOOGLE_SERVICE_ACCOUNT_JSON found or failed to write.")
