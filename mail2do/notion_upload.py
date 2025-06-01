#!/usr/bin/env python3
"""
notion_upload.py

Uploads tasks (from tasks.json) to a Notion database and writes a pure-JSON
summary of results to STDOUT.

Usage:
    python notion_upload.py tasks.json > upload_results.json
"""

import json, os, sys, time, requests
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

NOTION_VERSION = "2022-06-28"
BLOCKED_TASK_NAMES = {"ToDo", "Task", "Untitled", "(unnamed task)"}

# ------------- helpers -----------------------------------------------------

def n_headers(token: str, ver: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": ver,
        "Content-Type": "application/json",
    }

def make_prop(ptype: str, value: Any, people_map: dict) -> Optional[Dict[str, Any]]:
    if value is None or value == "" or (isinstance(value, list) and not value):
        return None
    if ptype == "title":
        txt = value if isinstance(value, str) else str(value[0])
        return {"title": [{"type": "text", "text": {"content": txt}}]}
    if ptype == "rich_text":
        txt = value if isinstance(value, str) else str(value[0])
        return {"rich_text": [{"type": "text", "text": {"content": txt}}]}
    if ptype == "url":
        return {"url": str(value)}
    if ptype == "date":
        return {"date": {"start": str(value)}}
    if ptype == "number":
        try:
            return {"number": float(value)}
        except ValueError:
            return None
    if ptype in {"select", "status"}:
        return {ptype: {"name": str(value)}}
    if ptype == "multi_select":
        vals = value if isinstance(value, list) else [value]
        return {"multi_select": [{"name": str(v)} for v in vals]}
    if ptype == "people":
        names = value if isinstance(value, list) else [value]
        ids = [{"object": "user", "id": people_map[n]}
               for n in names if n in people_map]
        return {"people": ids} if ids else None
    if ptype == "relation":
        ids = value if isinstance(value, list) else [value]
        return {"relation": [{"id": i} for i in ids]}
    return None

def page_exists(token: str, ver: str, db_id: str,
                title_prop: str, task_name: str) -> bool:
    if not task_name:
        return False
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = n_headers(token, ver)
    payload = {
        "filter": {"property": title_prop, "title": {"equals": task_name}},
        "page_size": 1,
    }
    try:
        r = requests.post(url, headers=headers, json=payload)
        return r.ok and bool(r.json().get("results"))
    except Exception:
        return False

# ------------- main --------------------------------------------------------

def main() -> None:
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    db_id = os.getenv("NOTION_DATABASE_ID")
    ver   = os.getenv("NOTION_VERSION", NOTION_VERSION)
    if not token or not db_id:
        sys.exit("ERROR: NOTION_TOKEN and NOTION_DATABASE_ID must be set in .env")

    if len(sys.argv) != 2:
        sys.exit("Usage: python notion_upload.py tasks.json")
    tasks = json.load(open(sys.argv[1], encoding="utf-8"))

    headers = n_headers(token, ver)

    # fetch DB schema & find the title property key
    sch_resp = requests.get(f"https://api.notion.com/v1/databases/{db_id}",
                            headers=headers).json()
    schema = sch_resp["properties"]
    title_prop_key = next(k for k, v in schema.items() if v["type"] == "title")

    # build people map (name/email → id)
    people_map: Dict[str, str] = {}
    cursor = None
    while True:
        url = "https://api.notion.com/v1/users"
        params = {"start_cursor": cursor} if cursor else {}
        r = requests.get(url, headers=headers, params=params).json()
        for u in r.get("results", []):
            if u["type"] == "person":
                uid = u["id"]
                if u.get("name"):
                    people_map[u["name"]] = uid
                if u["person"].get("email"):
                    people_map[u["person"]["email"]] = uid
        if not r.get("has_more"):
            break
        cursor = r.get("next_cursor")

    results: List[Dict[str, str]] = []

    for task in tasks:
        name = task.get("Task name") or ""
        if name.strip() in BLOCKED_TASK_NAMES:
            results.append({"task": name or "(unnamed)", "status": "skipped (generic name)"})
            continue
        if page_exists(token, ver, db_id, title_prop_key, name):
            results.append({"task": name, "status": "skipped (already exists)"})
            continue

        props = {}
        for k, v in task.items():
            if k in schema:
                prop_payload = make_prop(schema[k]["type"], v, people_map)
                if prop_payload:
                    props[k] = prop_payload

        if not props:
            results.append({"task": name or "(unnamed)", "status": "failed (no mappable fields)"})
            continue

        body = {"parent": {"database_id": db_id}, "properties": props}
        resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=body)
        if resp.ok:
            results.append({"task": name, "status": "created"})
        else:
            err = resp.json().get("message", resp.text)
            results.append({"task": name, "status": f"failed ({err})"})
        time.sleep(0.4)  # rate-limit cushion

    # *** ONLY JSON TO STDOUT ***
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
