#!/usr/bin/env python3
"""
fetch_emails.py – dump a folder's mail to JSON keyed by IMAP UID.
"""

import os, imaplib, email, json
from email.header import decode_header
from typing import List
from dotenv import load_dotenv


def _decode_header_field(raw_header: str) -> str:
    parts = decode_header(raw_header)
    return "".join(
        frag.decode(enc or "utf-8", errors="ignore") if isinstance(frag, bytes) else frag
        for frag, enc in parts
    )


def fetch_emails() -> None:
    load_dotenv()
    host     = os.getenv("IMAP_HOST")
    port     = int(os.getenv("IMAP_PORT", "993"))
    user     = os.getenv("IMAP_USER")
    password = os.getenv("IMAP_PASSWORD")
    folder   = os.getenv("EMAIL_FOLDER", "INBOX")

    if not all([host, user, password]):
        raise RuntimeError("IMAP_HOST, IMAP_USER or IMAP_PASSWORD missing in .env")

    result: dict[str, dict] = {}

    with imaplib.IMAP4_SSL(host, port) as imap:
        imap.login(user, password)
        if imap.select(folder, readonly=True)[0] != "OK":
            raise RuntimeError(f"Cannot open folder {folder}")

        status, msg_nums = imap.search(None, "ALL")
        if status != "OK":
            raise RuntimeError("Search failed")

        for seq in msg_nums[0].split():                       # sequence numbers
            status, data = imap.fetch(seq, "(UID RFC822)")    # pull UID + full message
            if status != "OK":
                continue

            # data[0] is a tuple: (b'SEQ (UID <uid> RFC822 {n}', raw_email)
            raw_meta, raw_email = data[0]
            uid = int(raw_meta.split()[2])                    # third token is UID

            msg = email.message_from_bytes(raw_email)
            subject = _decode_header_field(msg.get("Subject", "(No subject)"))

            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain" and \
                       "attachment" not in (part.get("Content-Disposition") or ""):
                        body_text = part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8",
                            errors="ignore",
                        )
                        break
            else:
                body_text = msg.get_payload(decode=True).decode(
                    msg.get_content_charset() or "utf-8",
                    errors="ignore",
                )

            result[str(uid)] = {
                "uid": uid,
                "subject": subject,
                "body": body_text.strip(),
            }

        imap.logout()

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    fetch_emails()

