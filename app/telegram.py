import os
import requests
import html

def send(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        },
        timeout=20
    )
    r.raise_for_status()

def esc(value):
    return html.escape(str(value or ""))

def money(job):
    return esc(job.get("salary") or "Not specified")

def build(jobs):
    lines = [
        "<b>🚀 Daily Internship Shortlist</b>",
        f"<b>{len(jobs)} best matches</b>",
        ""
    ]
    for i, job in enumerate(jobs[:20], 1):
        lines.extend([
            f"<b>{i}. {esc(job['title'])}</b>",
            f"🏢 {esc(job['company'])}",
            f"📍 {esc(job['location'])}",
            f"🌐 {esc(job['work_mode'])}",
            f"💰 {money(job)}",
            f"🎯 Match: <b>{job['score']}/100</b>",
            f"🔎 {esc('; '.join(job.get('reasons', [])) or 'Profile match')}",
            f"🔗 <a href=\"{esc(job['url'])}\">Apply / View Job</a>",
            ""
        ])
    lines.append("Filters: no pure backend, stipend > ₹20k when stated, on-site ≤2 months, hybrid ≤3 months, remote <8 months.")
    return "\n".join(lines)
