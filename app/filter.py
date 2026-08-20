import re
from datetime import datetime, timezone

INR_PER_USD = 88.0
INR_PER_EUR = 103.0
INR_PER_GBP = 118.0

def text(job):
    return " ".join([
        job.get("title", ""),
        job.get("description", ""),
        job.get("job_type", ""),
        job.get("location", ""),
        job.get("work_mode", "")
    ]).lower()

def is_internship(job):
    t = text(job)
    title = job.get("title", "").lower()
    return (
        "intern" in title
        or "internship" in t
        or "internship" in job.get("job_type", "").lower()
    )

def blocked_role(job, profile):
    title = job.get("title", "").lower()
    for role in profile["blocked_roles"]:
        if role in title:
            return True
    return False

def role_match(job, profile):
    title = job.get("title", "").lower()
    return any(role in title for role in profile["target_roles"])

def mode(job):
    return job.get("work_mode", "").lower()

def parse_duration_months(job):
    t = text(job)
    patterns = [
        (r"(\d+(?:\.\d+)?)\s*(?:months?|mos?)", lambda x: float(x)),
        (r"(\d+(?:\.\d+)?)\s*(?:weeks?|wks?)", lambda x: float(x) / 4.345),
        (r"(\d+(?:\.\d+)?)\s*(?:days?)", lambda x: float(x) / 30.44)
    ]
    values = []
    for pat, fn in patterns:
        for m in re.finditer(pat, t):
            try:
                values.append(fn(m.group(1)))
            except ValueError:
                pass
    return min(values) if values else None

def duration_ok(job, profile):
    m = mode(job)
    months = parse_duration_months(job)
    t = text(job)
    if m == "remote":
        return months is None or months < 8
    if m == "hybrid":
        if months is not None and months > 3:
            return False
        if re.search(r"\b4\s*months?\b|\b5\s*months?\b|\b6\s*months?\b|\b7\s*months?\b|\b8\s*months?\b", t):
            return False
        return True
    if m == "onsite":
        if months is not None and months > 2:
            return False
        if re.search(r"\b3\s*months?\b|\b4\s*months?\b|\b5\s*months?\b|\b6\s*months?\b", t):
            return False
        return True
    return True

def salary_monthly_inr(job):
    s = job.get("salary", "")
    if not s:
        return None
    t = s.lower().replace(",", "").replace("₹", " inr ")
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)]
    if not nums:
        return None
    lo = min(nums)
    if "usd" in t or "$" in s:
        lo *= INR_PER_USD
    elif "eur" in t or "€" in s:
        lo *= INR_PER_EUR
    elif "gbp" in t or "£" in s:
        lo *= INR_PER_GBP
    if "year" in t or "/yr" in t or "annual" in t:
        lo /= 12
    elif "week" in t:
        lo *= 4.345
    elif "day" in t:
        lo *= 30.44
    return lo

def salary_ok(job):
    monthly = salary_monthly_inr(job)
    if monthly is None:
        return True
    return monthly > 20000

def fresh_days(job):
    value = job.get("created", "")
    if not value:
        return 999
    try:
        value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - dt).days)
    except Exception:
        return 999

def passes(job, profile):
    if not is_internship(job):
        return False, "Not clearly an internship"
    if blocked_role(job, profile):
        return False, "Pure backend role"
    if not role_match(job, profile):
        return False, "Role does not match target roles"
    if not salary_ok(job):
        return False, "Explicit compensation is at or below ₹20,000/month"
    if not duration_ok(job, profile):
        return False, "Duration violates work-mode availability"
    return True, ""

def score(job, profile):
    t = text(job)
    title = job.get("title", "").lower()
    score = 0
    reasons = []
    matched = []
    for skill in profile["skills"]:
        if skill.lower() in t:
            matched.append(skill)
    score += min(45, len(set(matched)) * 4)
    if role_match(job, profile):
        score += 25
    if job.get("work_mode") == "remote":
        score += 8
    if job.get("work_mode") == "hybrid":
        score += 6
    if "intern" in title:
        score += 5
    days = fresh_days(job)
    if days <= 1:
        score += 12
    elif days <= 3:
        score += 8
    elif days <= 7:
        score += 4
    if salary_monthly_inr(job):
        if salary_monthly_inr(job) >= 50000:
            score += 5
        elif salary_monthly_inr(job) > 20000:
            score += 3
    if matched:
        reasons.append("Skills: " + ", ".join(matched[:8]))
    if days <= 7:
        reasons.append(f"Posted about {days} day(s) ago")
    return min(100, score), reasons

def rank(jobs, profile):
    out = []
    for job in jobs:
        ok, reason = passes(job, profile)
        if not ok:
            continue
        s, reasons = score(job, profile)
        job["score"] = s
        job["reasons"] = reasons
        out.append(job)
    out.sort(key=lambda x: (x["score"], -fresh_days(x)), reverse=True)
    return out
