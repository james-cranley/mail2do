# ✅mail2do

**✅mail2do** is an automated pipeline that converts actionable emails into Notion database tasks using IMAP, OpenAI, and the Notion API. At present mail2do identifies a single task per email.

NB use the `multi-task` branch where the LLM can extract multiple tasks per email.

---

## Overview

1. **Extracts emails from IMAP**
2. **Detects your Notion database schema and allowed field values**
3. **Uses an LLM (OpenAI GPT) to parse emails into Notion task objects**
4. **Uploads new, deduplicated tasks to Notion**

---

## Directory Structure

```
.
├── .env.example              # Example environment variables to copy and modify
├── .env                      # All secrets and configuration variables
├── mail2do/                  # Python package containing modules
│   ├── __init__.py
│   ├── add_date.py           # Prepends current date/time to prompt.txt
│   ├── fetch_emails.py       # Exports emails from IMAP to JSON
│   ├── notion_get_schema.py  # Dumps Notion DB schema + allowed values
│   ├── parse_emails.py       # LLM parser: emails + schema → tasks
│   └── notion_upload.py      # Uploads tasks.json as new Notion pages
├── prompt.txt                # LLM system prompt template (auto-updated)
├── reset.sh                  # Helper to delete temporary files
├── README.md                 # Project documentation
├── run_mail2do.sh            # Runscript for pipeline (configure manually)
└── setup.py                  # Installable package configuration
```

---

## Installation & Setup (Package)

### Using Conda (optional)

Create and activate a Conda environment with Python and the package in editable mode:

```sh
conda env create -f environment.yml
conda activate mail2do
```

### 1. Install with pip

```sh
pip install mail2do
```

### 2. **Configure your `.env`**

You can configure your environment file either manually or using an interactive wizard:

**Manual copy:**

```sh
cp .env.example .env
# Edit .env with your IMAP, Notion, and OpenAI details
```

**Interactive wizard:**

```sh
mail2do-configure
```

Example `.env.example` contents:

```dotenv
# IMAP settings
IMAP_HOST=mail.example.com
IMAP_PORT=993
IMAP_USER=your.email@example.com
IMAP_PASSWORD=yourpassword
EMAIL_FOLDER=ToDo

# Notion settings
NOTION_TOKEN=secret_abc123
NOTION_DATABASE_ID=xxxxxxxxxxxxxxx

# OpenAI settings
OPENAI_API_KEY=sk-xxxxxxx
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.3
LLM_PROMPT=prompt.txt
```

---

## How the Pipeline Works

The pipeline is modular.  
**You can run each step independently, or use the provided `pipeline.sh` for all steps.**

**Typical workflow (after installation):**

```sh
mail2do-fetch-emails > emails.json
mail2do-get-schema  > schema.json
mail2do-parse-emails emails.json schema.json > tasks.json
mail2do-upload       tasks.json         > upload_results.json
```

**Full pipeline (all steps):**

```sh
mail2do
```

---

### Step-by-Step

#### 1. **mail2do-fetch-emails**

- Connects to your IMAP mailbox and exports all emails (from the specified folder) as a JSON list of subject/body/uid.
- **Config:** Reads IMAP_* and EMAIL_FOLDER from `.env`.
- **Output:** `emails.json`

#### 2. **mail2do-get-schema**

- Fetches the schema of your target Notion database, including all relation/rollup fields and allowed property values (for select, status, etc).
- **Config:** Reads NOTION_TOKEN, NOTION_DATABASE_ID from `.env`.
- **Output:** `schema.json`

#### 3. **mail2do-parse-emails**

- For each email:
   - Uses OpenAI LLM to extract structured tasks matching your Notion DB schema.
   - The prompt always includes today's date (via `add_date.py`).
   - Skips previously processed emails using `processed_emails.txt`.
   - Outputs a list of tasks in JSON.
- **Config:** Uses OpenAI variables and the LLM_PROMPT from `.env`.
- **Output:** `tasks.json`

#### 4. **mail2do-upload**

- For each task, checks if a task with the same "Task name" already exists in Notion (deduplication).
- Skips tasks with fallback/generic names (e.g. "ToDo", "Task", etc).
- Maps user names to Notion user IDs.
- Creates Notion pages for new tasks only.
- **Config:** Reads NOTION_TOKEN, NOTION_DATABASE_ID from `.env`.
- **Output:** `upload_results.json` (a JSON array of `{task, status}` dicts)

---

## Example: `upload_results.json`

```json
[
  {"task": "Construct weekly tiemtable", "status": "created"},
  {"task": "Return defective item", "status": "created"},
  {"task": "Add Alice's on-call dates...", "status": "skipped (already exists)"}
]
```

---

## Adding Today's Date to the Prompt

The helper `add_date.py` is called by `parse_emails.py` before each LLM run.  
It ensures that `prompt.txt` always begins with:

```
# Current date: 2025-06-01 12:34
```

so the LLM always knows the "current" date and can fill the correct date field.

---

## Auto-Running

You can set this to run every x minutes, e.g. on a raspberry pi.

```
nano run_mail2do.sh # edit with the path to mail2do and your conda installation
chmod +x run_mail2do.sh # make it executable
```

Edit crontab (run `crontab -e`) to add:

```
*/2 * * * * flock -n /tmp/mail2do.lock bash /home/jjc/mail2do/run_mail2do.sh >> /home/jjc/mail2do/cron.log 2>&1
```

---

## Troubleshooting

**IMAP errors:**  
- Double-check credentials and server host/port
- For Gmail, Outlook, and some providers, you may need an "App Password"
- Use the full email address as IMAP user if needed

**OpenAI errors:**  
- Ensure your key is correct and not rate-limited

**Notion errors:**  
- Confirm that your integration is shared with the database
- If relation DBs are missing, check access and Notion integration permissions

---

## Customization

- Adjust `prompt.txt` for your desired LLM parsing style
- Change the field deduplication logic in `notion_upload.py` if needed (e.g., deduplicate by multiple fields)
- Swap out any part of the pipeline for your own integrations or additional processing

---

[James Cranley](mailto:james.cranley@doctors.org.uk)

---
