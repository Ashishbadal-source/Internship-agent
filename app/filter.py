import re
from datetime import datetime, timezone

INR_PER_USD = 88.0
INR_PER_EUR = 103.0
INR_PER_GBP = 118.0

ROLE_GROUPS = {
    "software": [
        "software engineer",
        "software engineering",
        "software developer",
        "software development",
        "sde",
        "swe"
    ],
    "full_stack": [
        "full stack",
        "fullstack"
    ],
    "data_science": [
        "data science",
        "data scientist"
    ],
    "data_analyst": [
        "data analyst",
        "data analytics",
        "business analyst"
    ],
    "ml": [
        "machine learning",
        "ml engineer",
        "ml intern",
        "machine learning engineer"
    ],
    "ai": [
        "artificial intelligence",
        "ai engineer",
        "ai/ml",
        "ai ml",
        "ai intern"
    ],
    "python": [
        "python developer",
        "python engineer",
        "python intern"
    ]
}

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
    description = job.get("description", "").lower()

    blocked = profile.get("blocked_roles", [])

    for role in blocked:
        role = role.lower()
        if role in title:
            return True

    backend_patterns = [
        "backend developer",
        "backend engineer",
        "backend development",
        "back-end developer",
        "back-end engineer",
        "back end developer",
        "back end engineer"
    ]

    target_context = any(
        word in title
        for word in [
            "software engineer",
            "software developer",
            "sde",
            "swe",
            "full stack",
            "fullstack",
            "ai",
            "machine learning",
            "ml",
            "data science",
            "data analyst"
        ]
    )

    if any(pattern in title for pattern in backend_patterns) and not target_context:
        return True

    return False

def role_match(job, profile):
    title = job.get("title", "").lower()

    for role in profile.get("target_roles", []):
        role = role.lower()
        if role in title:
            return True

    for group in ROLE_GROUPS.values():
        matches = [x for x in group if x in title]
        if matches:
            return True

    return False

def matched_role_groups(job):
    title = job.get("title", "").lower()
    groups = []

    for group, keywords in ROLE_GROUPS.items():
        if any(keyword in title for keyword in keywords):
            groups.append(group)

    return groups

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

    for pattern, converter in patterns:
        for match in re.finditer(pattern, t):
            try:
                values.append(converter(match.group(1)))
            except ValueError:
                pass

    return min(values) if values else None

def duration_ok(job, profile):
    work_mode = mode(job)
    months = parse_duration_months(job)

    if work_mode == "remote":
        return months is None or months < 8

    if work_mode == "hybrid":
        return months is None or months <= 3

    if work_mode == "onsite":
        return months is None or months <= 2

    return True

def salary_monthly_inr(job):
    salary = job.get("salary", "")

    if not salary:
        return None

    t = salary.lower().replace(",", "").replace("₹", " inr ")

    nums = [
        float(x)
        for x in re.findall(r"\d+(?:\.\d+)?", t)
    ]

    if not nums:
        return None

    low = min(nums)

    if "usd" in t or "$" in salary:
        low *= INR_PER_USD
    elif "eur" in t or "€" in salary:
        low *= INR_PER_EUR
    elif "gbp" in t or "£" in salary:
        low *= INR_PER_GBP

    if "year" in t or "/yr" in t or "annual" in t:
        low /= 12
    elif "week" in t:
        low *= 4.345
    elif "day" in t:
        low *= 30.44

    return low

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

        return max(
            0,
            (datetime.now(timezone.utc) - dt).days
        )

    except Exception:
        return 999

def location_score(job, profile):
    location = job.get("location", "").lower()
    work_mode = mode(job)

    preferred = [
        x.lower()
        for x in profile.get("preferred_locations", [])
    ]

    if work_mode == "remote":
        return 10

    if any(place in location for place in preferred):
        return 10

    if "india" in location:
        return 7

    return 3

def skill_score(job, profile):
    t = text(job)

    matched = []

    for skill in profile.get("skills", []):
        skill_lower = skill.lower()

        if skill_lower in t:
            matched.append(skill)

    unique = list(dict.fromkeys(matched))

    if len(unique) >= 8:
        points = 30
    elif len(unique) >= 6:
        points = 27
    elif len(unique) >= 5:
        points = 24
    elif len(unique) >= 4:
        points = 21
    elif len(unique) >= 3:
        points = 17
    elif len(unique) >= 2:
        points = 12
    elif len(unique) == 1:
        points = 7
    else:
        points = 0

    return points, unique

def role_score(job):
    title = job.get("title", "").lower()
    groups = matched_role_groups(job)

    if not groups:
        return 0, []

    score = 25

    if "software" in groups:
        score += 5

    if "full_stack" in groups:
        score += 7

    if "data_science" in groups:
        score += 5

    if "ml" in groups:
        score += 7

    if "ai" in groups:
        score += 7

    if "data_analyst" in groups:
        score += 4

    if "intern" in title:
        score += 3

    return min(35, score), groups

def domain_score(job):
    t = text(job)

    score = 0

    ai_words = [
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "computer vision",
        "natural language processing",
        "nlp",
        "generative ai",
        "llm",
        "pytorch",
        "tensorflow"
    ]

    data_words = [
        "data science",
        "data analysis",
        "data analytics",
        "sql",
        "pandas",
        "numpy",
        "scikit-learn"
    ]

    if any(word in t for word in ai_words):
        score += 10

    if any(word in t for word in data_words):
        score += 5

    return min(15, score)

def freshness_score(job):
    days = fresh_days(job)

    if days <= 1:
        return 5

    if days <= 3:
        return 4

    if days <= 7:
        return 3

    if days <= 14:
        return 1

    return 0

def stipend_score(job):
    monthly = salary_monthly_inr(job)

    if monthly is None:
        return 2

    if monthly >= 50000:
        return 5

    if monthly > 20000:
        return 4

    return 0

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
    role_points, role_groups = role_score(job)
    skills_points, matched_skills = skill_score(job, profile)
    domain_points = domain_score(job)
    location_points = location_score(job, profile)
    freshness_points = freshness_score(job)
    stipend_points = stipend_score(job)

    total = (
        role_points
        + skills_points
        + domain_points
        + location_points
        + freshness_points
        + stipend_points
    )

    reasons = []

    if role_groups:
        readable = {
            "software": "Software Engineering",
            "full_stack": "Full Stack",
            "data_science": "Data Science",
            "data_analyst": "Data Analytics",
            "ml": "Machine Learning",
            "ai": "AI",
            "python": "Python"
        }

        reasons.append(
            "Role: " +
            ", ".join(
                readable.get(group, group)
                for group in role_groups
            )
        )

    if matched_skills:
        reasons.append(
            "Skills: " +
            ", ".join(matched_skills[:8])
        )

    if mode(job) == "remote":
        reasons.append("Remote")

    elif mode(job) == "hybrid":
        reasons.append("Hybrid")

    days = fresh_days(job)

    if days <= 7:
        reasons.append(
            f"Posted about {days} day(s) ago"
        )

    monthly = salary_monthly_inr(job)

    if monthly is not None:
        reasons.append(
            f"Stipend approx ₹{int(monthly):,}/month"
        )

    return min(100, total), reasons

def rank(jobs, profile):
    out = []

    for job in jobs:
        ok, reason = passes(job, profile)

        if not ok:
            continue

        job_score, reasons = score(job, profile)

        job["score"] = job_score
        job["reasons"] = reasons

        out.append(job)

    out.sort(
        key=lambda x: (
            x["score"],
            -fresh_days(x)
        ),
        reverse=True
    )

    return out
