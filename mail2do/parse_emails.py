#!/usr/bin/env python3
"""
parse_emails.py

Converts emails (from fetch_emails.py) into Notion to-do items using an LLM,
using the schema and example field values from notion_get_schema.py.

Usage:
    python parse_emails.py [--ignore-log] emails.json schema.json > tasks.json

Dependencies: openai>=1.0.0, python-dotenv

Environment (.env):
    OPENAI_API_KEY
    OPENAI_MODEL
    OPENAI_TEMPERATURE
    LLM_PROMPT
    NOTION_DATABASE_ID
"""

import os, sys, json, argparse, time, re
from typing import Dict, Any, List
from dotenv import load_dotenv
import openai
from mail2do.add_date import prepend_date

LOG_FILE = "processed_emails.txt"

def canonical_id(s: str) -> str:
    return s.replace("-", "") if s else s

def load_prompt(path: str) -> str:
    prepend_date(path)               # ← NEW: stamp the date
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()

json_pattern = re.compile(r"\{.*\}", re.DOTALL)

def force_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    m = json_pattern.search(text)
    if not m:
        raise ValueError("No JSON object detected in model reply")
    return json.loads(m.group(0))

def openai_chat(client, system_prompt: str, user_prompt: str,
                model: str, temperature: float) -> Dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)

def parse_email_to_task(uid: str, mail: Dict[str, str],
                        schema_props: Dict[str, Any],
                        ref_for_prompt: Dict[str, List[str]],
                        sys_prompt: str, model: str, temp: float,
                        client) -> Dict[str, Any]:
    field_list = "\n".join(f"- {k} ({v['type']})" for k, v in schema_props.items())
    possible_values = ""
    if ref_for_prompt:
        possible_values = "\nHere are some existing values for some fields (use one of these if relevant):\n" + \
            "\n".join(f"- {k}: {v[:10]}" for k, v in ref_for_prompt.items())
    user_msg = (
        f"Here is the target Notion database schema (field name and type):\n"
        f"{field_list}\n"
        f"{possible_values}\n\n"
        f"Convert this email into a JSON object that fills as many of those "
        f"fields as possible. Use ONLY those field names, omit any unknowns, "
        f"and output *only* valid JSON (no markdown).\n\n"
        f"EMAIL UID: {uid}\n"
        f"Subject: {mail['subject']}\n"
        f"Body:\n{mail['body']}"
    )
    try:
        return openai_chat(client, sys_prompt, user_msg, model, temp)
    except json.JSONDecodeError:
        return force_json(openai_chat(client, sys_prompt, user_msg, model, temp))

def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--ignore-log", action="store_true",
                        help="process all emails regardless of processed_emails.txt")
    parser.add_argument("emails_json", help="path to fetch_emails.py output")
    parser.add_argument("schema_json", help="path to notion_get_schema.py output")
    args = parser.parse_args()

    api_key     = os.getenv("OPENAI_API_KEY")
    model       = os.getenv("OPENAI_MODEL", "gpt-4o")
    temp        = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    prompt_path = os.getenv("LLM_PROMPT", "prompt.txt")
    main_db_id  = canonical_id(os.getenv("NOTION_DATABASE_ID", ""))

    if not api_key or not main_db_id:
        sys.exit("ERROR: Missing OPENAI_API_KEY or NOTION_DATABASE_ID in .env")

    client = openai.OpenAI(api_key=api_key)

    with open(args.emails_json, "r", encoding="utf-8") as f:
        emails: Dict[str, Dict[str, str]] = json.load(f)

    with open(args.schema_json, "r", encoding="utf-8") as f:
        full_json = json.load(f)

    schema_all   = full_json["schema"]
    reference    = full_json.get("reference", {})
    if main_db_id not in schema_all:
        sys.exit(f"ERROR: main database ID {main_db_id} not found in schema.json")

    schema_props = schema_all[main_db_id]["properties"]
    ref_for_prompt = reference.get(main_db_id, {})
    system_prompt = load_prompt(prompt_path)

    processed: set[str] = set()
    if not args.ignore_log:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as lf:
                processed = {line.strip() for line in lf if line.strip()}
        else:
            print(f"WARNING: {LOG_FILE} not found; treating all emails as unprocessed.",
                  file=sys.stderr)

    tasks: List[Dict[str, Any]] = []
    new_uids: List[str] = []

    for uid, mail in emails.items():
        if not args.ignore_log and uid in processed:
            continue  # skip already parsed

        try:
            task = parse_email_to_task(uid, mail, schema_props, ref_for_prompt,
                                       system_prompt, model, temp, client)
            task["_mail2do_uid"] = uid
            tasks.append(task)
            new_uids.append(uid)
        except Exception as e:
            print(f"WARNING: email UID {uid} failed to parse – {e}", file=sys.stderr)
        time.sleep(0.3)   # respectful rate-limit


    print(json.dumps(tasks, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
