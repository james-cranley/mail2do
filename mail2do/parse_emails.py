#!/usr/bin/env python3
"""
parse_emails.py – converts fetched emails into Notion-ready tasks.
"""

import os, sys, json, argparse, time, re
from typing import Dict, Any, List
from dotenv import load_dotenv
import openai
from mail2do.add_date import prepend_date

LOG_FILE = "processed_emails.txt"

# -------------------------------------------------- helpers

def canonical_id(s: str) -> str:
    return s.replace("-", "") if s else s

def load_prompt(path: str) -> str:
    prepend_date(path)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()

json_block = re.compile(r"\[\s*{.*?}\s*]|{.*?}", re.DOTALL)

def force_json(text: str) -> dict | list:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    m = json_block.search(text)
    if not m:
        raise ValueError("No JSON object or array detected in model reply")
    return json.loads(m.group(0))

def openai_chat(client, system_prompt, user_prompt, model, temperature):
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content

def parse_email_to_tasks(uid, mail, schema_props, ref_for_prompt,
                         sys_prompt, model, temp, client) -> List[Dict[str, Any]]:
    field_list = "\n".join(f"- {k} ({v['type']})" for k, v in schema_props.items())
    possible_values = ""
    if ref_for_prompt:
        possible_values = "\nHere are some existing values for some fields (use one of these if relevant):\n" + \
                          "\n".join(f"- {k}: {v[:10]}" for k, v in ref_for_prompt.items())
    user_msg = (
        f"Here is the target Notion database schema (field name and type):\n"
        f"{field_list}\n"
        f"{possible_values}\n\n"
        f"Convert this email into a JSON array of objects (one per task), filling as many of those "
        f"fields as possible. Use ONLY those field names, omit any unknowns, "
        f"and output *only* valid JSON (no markdown). "
        f"Return only a single JSON array of objects. Do not wrap it in markdown.\n\n"
        f"EMAIL UID: {uid}\n"
        f"Subject: {mail['subject']}\n"
        f"Body:\n{mail['body']}"
    )
    reply = openai_chat(client, sys_prompt, user_msg, model, temp)
    try:
        data = json.loads(reply)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        obj = force_json(reply)
        return obj if isinstance(obj, list) else [obj]

# -------------------------------------------------- main

def main() -> None:
    load_dotenv()

    p = argparse.ArgumentParser()
    p.add_argument("emails_json")
    p.add_argument("schema_json")
    p.add_argument("-o", "--output", default="tasks.json",
                   help="write tasks to this file (default: tasks.json)")
    p.add_argument("--ignore-log", action="store_true",
                   help="process all emails, even if UID seen before")
    args = p.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    model   = os.getenv("OPENAI_MODEL", "gpt-4o")
    temp    = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    prompt_path = os.getenv("LLM_PROMPT", "prompt.txt")
    main_db = canonical_id(os.getenv("NOTION_DATABASE_ID", ""))

    if not api_key or not main_db:
        sys.exit("ERROR: missing OPENAI_API_KEY or NOTION_DATABASE_ID in .env")

    client = openai.OpenAI(api_key=api_key)

    emails = json.load(open(args.emails_json, encoding="utf-8"))
    full   = json.load(open(args.schema_json,  encoding="utf-8"))
    schema = full["schema"][main_db]["properties"]
    ref    = full.get("reference", {}).get(main_db, {})
    sys_prompt = load_prompt(prompt_path)

    processed = set()
    if not args.ignore_log and os.path.exists(LOG_FILE):
        processed = {l.strip() for l in open(LOG_FILE, encoding="utf-8") if l.strip()}

    tasks, new_uids = [], []
    for uid, mail in emails.items():
        if uid in processed and not args.ignore_log:
            continue
        try:
            new_tasks = parse_email_to_tasks(
                uid, mail, schema, ref, sys_prompt, model, temp, client
            )

            for t in new_tasks:
                t["_mail2do_uid"] = uid

            tasks.extend(new_tasks)
            new_uids.append(uid)
        except Exception as e:
            print(f"WARNING: email UID {uid} failed to parse – {e}", file=sys.stderr)
        time.sleep(0.3)

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(tasks, fh, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
