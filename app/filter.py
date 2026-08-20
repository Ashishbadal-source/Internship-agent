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
        "data analytics"
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
        job.get("work_mode", ""),
        job.get("salary", "")
    ]).lower()

def is_internship(job):
    title = job.get("title", "").lower()
    t = text(job)
    return "intern" in title or "internship" in t

def blocked_role(job, profile):
    title = job.get("title", "").lower()

    for role in profile.get("blocked_roles", []):
        if role.lower() in title:
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

    return any(x in title for x in backend_patterns)

def role_match(job, profile):
    title = job.get("title", "").lower()

    for role in profile.get("target_roles", []):
        if role.lower() in title:
            return True

    for keywords in ROLE_GROUPS.values():
        if any(keyword in title for keyword in keywords):
            return True

    return False

def matched_role_groups(job):
    title = job.get("title", "").lower()

    return [
        group
        for group, keywords in ROLE_GROUPS.items()
        if any(keyword in title for keyword in keywords)
    ]

def mode(job):
    return job.get("work_mode", "").lower()

def parse_duration_months(job):
    t = text(job)
    values = []

    patterns = [
        (r"(\d+(?:\.\d+)?)\s*(?:months?|mos?)", 1),
        (r"(\d+(?:\.\d+)?)\s*(?:weeks?|wks?)", 1 / 4.345),
        (r"(\d+(?:\.\d+)?)\s*(?:days?)", 1 / 30.44)
    ]

    for pattern, factor in patterns:
        for match in re.finditer(pattern, t):
            values.append(float(match.group(1)) * factor)

    return min(values) if values else None

def duration_ok(job, profile):
    months = parse_duration_months(job)

    if months is None:
        return True

    if mode(job) == "remote":
        return months < 8

    if mode(job) == "hybrid":
        return months <= 3

    if mode(job) == "onsite":
        return months <= 2

    return True

def salary_monthly_inr(job):
    salary = job.get("salary", "")

    if not salary:
        return None

    t = str(salary).lower().replace(",", "").replace("₹", " inr ")

    nums = [
        float(x)
        for x in re.findall(r"\d+(?:\.\d+)?", t)
    ]

    if not nums:
        return None

    value = min(nums)

    if "usd" in t or "$" in str(salary):
        value *= INR_PER_USD
    elif "eur" in t or "€" in str(salary):
        value *= INR_PER_EUR
    elif "gbp" in t or "£" in str(salary):
        value *= INR_PER_GBP

    if "year" in t or "/yr" in t or "annual" in t:
        value /= 12
    elif "week" in t:
        value *= 4.345
    elif "day" in t:
        value *= 30.44

    return value

def salary_ok(job):
    salary = job.get("salary", "")

    if not salary:
        return False

    monthly = salary_monthly_inr(job)

    if monthly is None:
        return False

    return monthly > 20000

def fresh_days(job):
    value = job.get("created", "")

    if not value:
        return 999

    try:
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return max(
            0,
            (datetime.now(timezone.utc) - dt).days
        )

    except Exception:
        return 999

def graduation_ok(job, profile):
    target_year = profile.get("target_year", 2028)
    t = text(job)

    years = []

    patterns = [
        r"(?:graduat(?:e|ing)|graduation|class of|batch of|students? graduating)\D{0,40}(20\d{2})",
        r"(20\d{2})\s*(?:graduat(?:e|ing)|graduation|batch|class)"
    ]

    for pattern in patterns:
        years.extend(
            int(x)
            for x in re.findall(pattern, t)
        )

    if not years:
        return True

    return target_year in years

def location_score(job, profile):
    location = job.get("location", "").lower()

    preferred = [
        x.lower()
        for x in profile.get("preferred_locations", [])
    ]

    if mode(job) == "remote":
        return 5

    if any(place in location for place in preferred):
        return 5

    if "india" in location:
        return 4

    return 2

def skill_score(job, profile):
    t = text(job)
    matched = []

    for skill in profile.get("skills", []):
        if skill.lower() in t:
            matched.append(skill)

    matched = list(dict.fromkeys(matched))

    if len(matched) >= 5:
        points = 20
    elif len(matched) == 4:
        points = 17
    elif len(matched) == 3:
        points = 14
    elif len(matched) == 2:
        points = 10
    elif len(matched) == 1:
        points = 6
    else:
        points = 0

    return points, matched

def role_score(job):
    groups = matched_role_groups(job)
    title = job.get("title", "").lower()

    if not groups:
        return 0, []

    score = 25

    if "full_stack" in groups:
        score += 8
    elif "ml" in groups or "ai" in groups:
        score += 8
    elif "data_science" in groups:
        score += 7
    elif "software" in groups:
        score += 6
    elif "data_analyst" in groups:
        score += 5
    elif "python" in groups:
        score += 5

    if "intern" in title:
        score += 2

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
        return 0

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

    if not graduation_ok(job, profile):
        return False, "Not compatible with 2028 graduation"

    if not salary_ok(job):
        return False, "Stipend not specified or is at/below ₹20,000"

    if not duration_ok(job, profile):
        return False, "Duration violates work-mode availability"

    return True, ""

def score(job, profile):
    role_points, role_groups = role_score(job)
    skill_points, matched_skills = skill_score(job, profile)
    domain_points = domain_score(job)
    location_points = location_score(job, profile)
    freshness_points = freshness_score(job)
    stipend_points = stipend_score(job)

    total = (
        role_points
        + skill_points
        + domain_points
        + location_points
        + freshness_points
        + stipend_points
    )

    reasons = []

    names = {
        "software": "Software Engineering",
        "full_stack": "Full Stack",
        "data_science": "Data Science",
        "data_analyst": "Data Analytics",
        "ml": "Machine Learning",
        "ai": "AI",
        "python": "Python"
    }

    if role_groups:
        reasons.append(
            "Role: " +
            ", ".join(
                names.get(group, group)
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
        ok, _ = passes(job, profile)

        if not ok:
            continue

        job["score"], job["reasons"] = score(
            job,
            profile
        )

        out.append(job)

    out.sort(
        key=lambda x: (
            x["score"],
            -fresh_days(x)
        ),
        reverse=True
    )

    return out
