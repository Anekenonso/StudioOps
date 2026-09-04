import os
import sys
import asyncio
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from backend.tools.parallel_client import ParallelClient


def sanitize(item):
    if isinstance(item, dict):
        out = {}
        for k, v in item.items():
            if any(s in k.lower() for s in ("key", "token", "secret", "authorization")):
                out[k] = "REDACTED"
            else:
                out[k] = v
        return out
    return item


async def main(query: str):
    api_key = os.getenv("PARALLEL_API_KEY")
    base_url = os.getenv("PARALLEL_BASE_URL")
    if not api_key or not base_url:
        print("ERROR: PARALLEL_API_KEY or PARALLEL_BASE_URL not set in environment.")
        return 2

    client = ParallelClient(api_key=api_key, base_url=base_url)
    try:
        results = await client.search(query, limit=5)
    except Exception as e:
        print("ERROR: Parallel search failed:", str(e))
        return 3

    safe = [sanitize(r) for r in results]
    print(json.dumps(safe, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "StudioOps AI SaaS research"
    raise SystemExit(asyncio.run(main(q)))
