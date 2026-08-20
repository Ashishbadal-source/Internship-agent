import html
import os
import re
import requests
from bs4 import BeautifulSoup

TIMEOUT = 20

def clean_text(value):
    if not value:
        return ""
    value = BeautifulSoup(html.unescape(str(value)), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", value).strip()

def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=TIMEOUT, headers={"User-Agent": "internship-agent/1.0"})
    r.raise_for_status()
    return r.json()

def fetch_remotive():
    data = get_json("https://remotive.com/api/remote-jobs", {"limit": 100})
    jobs = []
    for x in data.get("jobs", []):
        jobs.append({
            "id": f"remotive:{x.get('id')}",
            "source": "Remotive",
            "title": x.get("title", ""),
            "company": x.get("company_name", ""),
            "location": x.get("candidate_required_location", "Remote"),
            "work_mode": "remote",
            "job_type": x.get("job_type", ""),
            "description": clean_text(x.get("description", "")),
            "salary": x.get("salary", ""),
            "created": x.get("publication_date", ""),
            "url": x.get("url", "")
        })
    return jobs

def fetch_jobicy():
    data = get_json("https://jobicy.com/api/v2/remote-jobs", {"count": 100})
    jobs = []
    for x in data.get("jobs", []):
        jt = x.get("jobType", [])
        if isinstance(jt, list):
            jt = ", ".join(jt)
        jobs.append({
            "id": f"jobicy:{x.get('id')}",
            "source": "Jobicy",
            "title": x.get("jobTitle", ""),
            "company": x.get("companyName", ""),
            "location": x.get("jobGeo", "Remote"),
            "work_mode": "remote",
            "job_type": jt,
            "description": clean_text(x.get("jobDescription", "")),
            "salary": format_salary(x.get("salaryMin"), x.get("salaryMax"), x.get("salaryCurrency"), x.get("salaryPeriod")),
            "created": x.get("pubDate", ""),
            "url": x.get("url", "")
        })
    return jobs

def format_salary(lo, hi, cur, period):
    if lo is None and hi is None:
        return ""
    cur = cur or ""
    period = period or ""
    if lo is None:
        return f"{hi} {cur} {period}".strip()
    if hi is None:
        return f"{lo} {cur} {period}".strip()
    return f"{lo}-{hi} {cur} {period}".strip()

def fetch_arbeitnow():
    data = get_json("https://www.arbeitnow.com/api/job-board-api")
    jobs = []
    for x in data.get("data", []):
        tags = x.get("tags", [])
        if isinstance(tags, list):
            tags = " ".join(tags)
        jobs.append({
            "id": f"arbeitnow:{x.get('slug') or x.get('id') or x.get('url')}",
            "source": "Arbeitnow",
            "title": x.get("title", ""),
            "company": x.get("company_name", ""),
            "location": x.get("location", ""),
            "work_mode": "remote" if x.get("remote") else "onsite",
            "job_type": tags,
            "description": clean_text(x.get("description", "")),
            "salary": "",
            "created": x.get("created_at", ""),
            "url": x.get("url", "")
        })
    return jobs

def fetch_adzuna():
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []
    terms = [
        "software engineer intern",
        "software developer intern",
        "full stack developer intern",
        "data science intern",
        "data analyst intern",
        "machine learning intern",
        "AI ML intern",
        "python developer intern"
    ]
    jobs = []
    for term in terms:
        data = get_json(
            "https://api.adzuna.com/v1/api/jobs/in/search/1",
            {
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": 50,
                "what": term,
                "where": "India",
                "content-type": "application/json",
                "sort_by": "date"
            }
        )
        for x in data.get("results", []):
            loc = x.get("location", {}).get("display_name", "")
            desc = clean_text(x.get("description", ""))
            jobs.append({
                "id": f"adzuna:{x.get('id')}",
                "source": "Adzuna",
                "title": x.get("title", ""),
                "company": x.get("company", {}).get("display_name", ""),
                "location": loc,
                "work_mode": infer_mode(desc, loc),
                "job_type": f"{x.get('contract_type', '')} {x.get('contract_time', '')}",
                "description": desc,
                "salary": format_adzuna_salary(x),
                "created": x.get("created", ""),
                "url": x.get("redirect_url", "")
            })
    return jobs

def format_adzuna_salary(x):
    lo = x.get("salary_min")
    hi = x.get("salary_max")
    if lo is None and hi is None:
        return ""
    if lo is None:
        return f"{hi} INR/year"
    if hi is None:
        return f"{lo} INR/year"
    return f"{lo}-{hi} INR/year"

def infer_mode(desc, loc):
    t = f"{desc} {loc}".lower()
    if "hybrid" in t:
        return "hybrid"
    if "remote" in t or "work from home" in t:
        return "remote"
    return "onsite"

def fetch_all():
    jobs = []
    for fn in (fetch_remotive, fetch_jobicy, fetch_arbeitnow, fetch_adzuna):
        try:
            jobs.extend(fn())
        except Exception as e:
            print(f"{fn.__name__} failed: {e}")
    unique = {}
    for job in jobs:
        key = job.get("url") or job.get("id")
        if key:
            unique[key] = job
    return list(unique.values())
