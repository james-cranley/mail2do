#!/usr/bin/env python3
"""
notion_get_schema.py

Fetches the schema and unique sample values from a Notion database and all
directly related databases (via relation properties).

Outputs JSON with:
- "schema": { ... }
- "reference": { ... }  # per-db, per-property, all unique allowed/used values

Requires .env with NOTION_TOKEN and NOTION_DATABASE_ID.
"""

import os
import sys
import json
import collections
import requests
from dotenv import load_dotenv

NOTION_VERSION = "2022-06-28"

def canonical_id(raw: str) -> str:
    return raw.replace("-", "") if raw else raw

def api_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

def fetch_database_or_warn(token, db_id, db_pool, missing):
    cid = canonical_id(db_id)
    if cid in db_pool:
        return db_pool[cid]
    rsp = requests.get(f"https://api.notion.com/v1/databases/{db_id}",
                       headers=api_headers(token))
    if rsp.status_code == 200:
        db_pool[cid] = rsp.json()
        return rsp.json()
    else:
        missing.add(db_id)
        return None

def property_id_map(db_json: dict) -> dict:
    return {prop.get("id").replace("-", ""): name for name, prop in db_json.get("properties", {}).items()}

def extract_schema(db_json: dict, db_pool: dict) -> dict:
    pid_to_name = property_id_map(db_json)
    out_props = {}
    for prop_name, p in db_json["properties"].items():
        ptype = p["type"]
        entry = {"type": ptype}
        if ptype == "relation":
            rel_db_id = p["relation"]["database_id"]
            rel_db = db_pool.get(canonical_id(rel_db_id))
            entry.update({
                "related_database_id": rel_db_id,
                "related_database_title": rel_db.get("title", [{}])[0].get("plain_text", "?") if rel_db else "?"
            })
        elif ptype == "rollup":
            rl = p["rollup"]
            rel_prop_id   = rl.get("relation_property_id", "").replace("-", "")
            roll_prop_id  = rl.get("rollup_property_id", "").replace("-", "")
            entry["relation_property_id"]   = rl.get("relation_property_id")
            entry["relation_property_name"] = pid_to_name.get(rel_prop_id, "?")
            entry["rollup_property_id"]     = rl.get("rollup_property_id")
            parent_rel_prop = db_json["properties"].get(entry["relation_property_name"])
            target_db_id    = parent_rel_prop["relation"]["database_id"] if parent_rel_prop else None
            target_db       = db_pool.get(canonical_id(target_db_id)) if target_db_id else None
            if target_db:
                target_pid_map = property_id_map(target_db)
                entry["rollup_property_name"] = target_pid_map.get(roll_prop_id, "?")
                entry["related_database_id"]    = target_db_id
                entry["related_database_title"] = target_db.get("title", [{}])[0].get("plain_text", "?")
        out_props[prop_name] = entry
    return {
        "id": db_json["id"],
        "title": "".join(t.get("plain_text", "") for t in db_json.get("title", [])) or "(Untitled)",
        "properties": out_props,
    }

def collect_reference_rows(token, db_json, max_rows=10000):
    url = f"https://api.notion.com/v1/databases/{db_json['id']}/query"
    headers = api_headers(token)
    # ---- First: build schema-based value sets for select/multi_select/status ----
    ref = {}
    for name, prop in db_json['properties'].items():
        typ = prop['type']
        if typ in {'select', 'multi_select', 'status'}:
            options = [opt['name'] for opt in prop[typ]['options']]
            if options:
                ref[name] = set(options)
    # ---- Now enumerate all pages to get all titles, relations, people, etc ----
    rows = []
    next_cursor = None
    while True:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor
        resp = requests.post(url, headers=headers, json=payload)
        if not resp.ok:
            break
        result = resp.json()
        rows.extend(result.get("results", []))
        next_cursor = result.get("next_cursor")
        if not result.get("has_more"):
            break
        if len(rows) >= max_rows:
            break  # avoid runaways
    # ---- From page data ----
    for row in rows:
        for name, cell in row["properties"].items():
            typ = cell["type"]
            if typ == "title":
                txt = "".join(t["plain_text"] for t in cell[typ])
                if txt:
                    ref.setdefault(name, set()).add(txt)
            elif typ == "people" and cell["people"]:
                for p in cell["people"]:
                    if p.get("name"):
                        ref.setdefault(name, set()).add(p["name"])
            elif typ == "relation" and cell["relation"]:
                for rel in cell["relation"]:
                    if rel.get("id"):
                        ref.setdefault(name, set()).add(rel["id"])
            # You can add more types as needed
    # ---- Convert all sets to sorted lists ----
    for k in ref:
        if isinstance(ref[k], set):
            ref[k] = sorted(ref[k])
    return ref

def main():
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    main_id = os.getenv("NOTION_DATABASE_ID")
    if not token or not main_id:
        sys.exit("ERROR: NOTION_TOKEN or NOTION_DATABASE_ID missing in .env")
    db_pool, missing = {}, set()
    bfs = collections.deque([main_id])
    while bfs:
        db_id = bfs.popleft()
        db_json = fetch_database_or_warn(token, db_id, db_pool, missing)
        if not db_json:
            continue
        for prop in db_json["properties"].values():
            if prop["type"] == "relation":
                rel_db_id = prop["relation"]["database_id"]
                if canonical_id(rel_db_id) not in db_pool:
                    bfs.append(rel_db_id)
    schema_out, ref_out = {}, {}
    for cid, db_json in db_pool.items():
        schema_out[cid] = extract_schema(db_json, db_pool)
        ref_out[cid]    = collect_reference_rows(token, db_json)
    result = {"schema": schema_out, "reference": ref_out}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    for db_id in sorted(missing):
        print(
            f"Access to database {db_id} is required, please add this as a Connection on notion.so",
            file=sys.stderr,
        )

if __name__ == "__main__":
    main()
