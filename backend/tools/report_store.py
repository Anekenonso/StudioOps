import os
import json
from datetime import datetime
from typing import Any, Dict


REPORT_DIR = os.path.join(os.getcwd(), "outputs", "reports")


def ensure_dir():
    os.makedirs(REPORT_DIR, exist_ok=True)


def save_report_json(report: Dict[str, Any]) -> str:
    ensure_dir()
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"report_{ts}.json"
    path = os.path.join(REPORT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def save_report_markdown(report: Dict[str, Any]) -> str:
    ensure_dir()
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"report_{ts}.md"
    path = os.path.join(REPORT_DIR, filename)
    md = [f"# {report.get('project', {}).get('title','Report')}\n"]
    es = report.get("report", {}).get("executive_summary")
    if es:
        md.append("## Executive Summary\n")
        md.append(es + "\n")

    sources = report.get("report", {}).get("sources") or []
    if sources:
        md.append("## Sources\n")
        for s in sources:
            title = s.get("title") or s.get("url")
            url = s.get("url")
            md.append(f"- [{title}]({url})\n")

    with open(path, "w", encoding="utf-8") as f:
        f.writelines([l if l.endswith("\n") else l + "\n" for l in md])
    return path
