import os
import sys
import asyncio
import json
import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def sanitize(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if any(s in k.lower() for s in ("key", "token", "secret", "authorization", "api")):
                out[k] = "REDACTED"
            else:
                out[k] = sanitize(v)
        return out
    if isinstance(obj, list):
        return [sanitize(i) for i in obj]
    return obj


async def probe(query: str):
    key = os.getenv("PARALLEL_API_KEY")
    base = os.getenv("PARALLEL_BASE_URL")
    if not key or not base:
        print("PARALLEL_API_KEY or PARALLEL_BASE_URL missing")
        return 2

    endpoints = ["/search", "/v1/search", "/api/search", "/search/v1"]
    header_variants = [
        {"Authorization": f"Bearer {key}"},
        {"x-api-key": key},
        {"api-key": key},
        {"Authorization": f"ApiKey {key}"},
        {"Authorization": f"Token {key}"},
        {"Authorization": key},
    ]

    payload = {"q": query, "limit": 3}

    async with httpx.AsyncClient(timeout=20.0) as client:
        for ep in endpoints:
            url = f"{base.rstrip('/')}{ep}"
            for headers in header_variants:
                try:
                    headers_full = {**headers, "Content-Type": "application/json", "Accept": "application/json"}
                    resp = await client.post(url, json=payload, headers=headers_full)
                except Exception as e:
                    print(f"{url} with {list(headers.keys())}: ERROR {e}")
                    continue

                print(f"Tried {url} with {list(headers.keys())} -> {resp.status_code}")
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except Exception:
                        print("200 OK but failed to parse JSON")
                        return 0
                    print("SUCCESS — sanitized response:")
                    print(json.dumps(sanitize(data), indent=2, ensure_ascii=False))
                    return 0
                elif resp.status_code == 401:
                    # keep probing
                    continue
                else:
                    # show snippet of response for diagnostics (non-sensitive)
                    text = resp.text
                    print(f"Response body (truncated): {text[:200]}")

    print("No successful auth pattern found. Check key, base URL, or vendor docs.")
    return 3


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "StudioOps research example"
    raise SystemExit(asyncio.run(probe(q)))
