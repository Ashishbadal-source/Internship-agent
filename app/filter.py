import re
from datetime import datetime, timezone

INR_PER_USD = 88.0
INR_PER_EUR = 103.0
INR_PER_GBP = 118.0

SKILL_ALIASES = {
    "python": ["python"],
    "c++": ["c++", "cpp"],
    "sql": ["sql"],
    "javascript": ["javascript", "js"],
    "react": ["react", "react.js", "reactjs"],
    "node.js": ["node.js", "nodejs", "node"],
    "express": ["express", "express.js"],
    "mongodb": ["mongodb", "mongo db"],
    "supabase": ["supabase"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "pytorch": ["pytorch"],
    "tensorflow": ["tensorflow"],
    "scikit-learn": [
        "scikit-learn",
        "sklearn"
    ],
    "machine learning": [
        "machine learning",
        "ml"
    ],
    "data science": [
        "data science"
    ],
    "data analysis": [
        "data analysis",
        "data analytics"
    ],
    "computer vision": [
        "computer vision",
        "opencv"
    ],
    "nlp": [
        "nlp",
        "natural language processing"
    ],
    "git": ["git", "github"],
    "docker": ["docker"],
    "rest api": [
        "rest api",
        "restful api",
        "rest apis"
    ],
    "mern": [
        "mern",
        "mern stack"
    ]
}

ROLE_GROUPS = {
    "software": [
        "software engineer",
        "software engineering",
        "software developer",
        "software development",
        "sde intern",
        "sde",
        "swe intern",
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
        "machine learning engineer",
        "ml engineer",
        "ml intern"
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

BLOCKED_PATTERNS = [
    "backend developer",
    "backend engineer",
    "backend development",
    "back-end developer",
    "back-end engineer",
    "back end developer",
    "back end engineer"
]

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

    return (
        "intern" in title
        or "internship" in t
    )

def blocked_role(job, profile):
    title = job.get(
        "title",
        ""
    ).lower()

    for role in profile.get(
        "blocked_roles",
        []
    ):
        if role.lower() in title:
            return True

    return any(
        pattern in title
        for pattern in BLOCKED_PATTERNS
    )

def matched_roles(job):
    title = job.get(
        "title",
        ""
    ).lower()

    matched = []

    for group, keywords in ROLE_GROUPS.items():
        if any(
            keyword in title
            for keyword in keywords
        ):
            matched.append(group)

    return matched

def role_match(job, profile):
    return bool(
        matched_roles(job)
    )

def parse_duration_months(job):
    t = text(job)

    values = []

    patterns = [
        (
            r"(\d+(?:\.\d+)?)\s*(?:months?|mos?)",
            1
        ),
        (
            r"(\d+(?:\.\d+)?)\s*(?:weeks?|wks?)",
            1 / 4.345
        ),
        (
            r"(\d+(?:\.\d+)?)\s*(?:days?)",
            1 / 30.44
        )
    ]

    for pattern, factor in patterns:
        for match in re.finditer(
            pattern,
            t
        ):
            values.append(
                float(match.group(1))
                * factor
            )

    return min(values) if values else None

def duration_ok(job, profile):
    months = parse_duration_months(job)

    if months is None:
        return True

    work_mode = job.get(
        "work_mode",
        ""
    ).lower()

    if work_mode == "onsite":
        return months <= 2

    if work_mode == "hybrid":
        return months <= 3

    if work_mode == "remote":
        return months < 8

    return True

def stipend_monthly_inr(job):
    description = job.get(
        "description",
        ""
    )

    salary = job.get(
        "salary",
        ""
    )

    source_text = f"{description} {salary}".lower()

    stipend_context = re.search(
        r"(stipend|monthly stipend|per month|\/month|monthly pay|monthly compensation|internship pay|paid internship|pay range|compensation)",
        source_text
    )

    if not stipend_context:
        return None

    context = source_text[
        max(
            0,
            stipend_context.start() - 100
        ):
        min(
            len(source_text),
            stipend_context.end() + 180
        )
    ]

    numbers = re.findall(
        r"(?:₹|rs\.?|inr|\$|usd|€|eur|£|gbp)?\s*"
        r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*"
        r"(?:k)?",
        context,
        re.I
    )

    if not numbers:
        return None

    values = []

    for number in numbers:
        try:
            value = float(
                number.replace(",", "")
            )

            if re.search(
                rf"{re.escape(number)}\s*k",
                context,
                re.I
            ):
                value *= 1000

            if "$" in context or "usd" in context:
                value *= INR_PER_USD

            elif "€" in context or "eur" in context:
                value *= INR_PER_EUR

            elif "£" in context or "gbp" in context:
                value *= INR_PER_GBP

            values.append(value)

        except ValueError:
            pass

    if not values:
        return None

    return max(values)

def salary_ok(job):
    stipend = stipend_monthly_inr(job)

    if stipend is None:
        return False

    return stipend > 20000

def fresh_days(job):
    value = job.get(
        "created",
        ""
    )

    if not value:
        return 999

    try:
        dt = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return max(
            0,
            (
                datetime.now(
                    timezone.utc
                ) - dt
            ).days
        )

    except Exception:
        return 999

def graduation_ok(job, profile):
    target_year = profile.get(
        "target_year",
        2028
    )

    t = text(job)

    years = []

    patterns = [
        r"(?:graduat(?:e|ing)|graduation|class of|batch of|students? graduating)\D{0,40}(20\d{2})",
        r"(20\d{2})\s*(?:graduat(?:e|ing)|graduation|batch|class)"
    ]

    for pattern in patterns:
        years.extend(
            int(x)
            for x in re.findall(
                pattern,
                t
            )
        )

    if not years:
        return True

    return target_year in years

def extract_job_skills(job, profile):
    t = text(job)

    found = []

    for profile_skill in profile.get(
        "skills",
        []
    ):
        aliases = SKILL_ALIASES.get(
            profile_skill.lower(),
            [profile_skill.lower()]
        )

        if any(
            re.search(
                r"(?<!\w)"
                + re.escape(alias)
                + r"(?!\w)",
                t
            )
            for alias in aliases
        ):
            found.append(
                profile_skill
            )

    return list(
        dict.fromkeys(found)
    )

def required_skills(job):
    t = text(job)

    required = []

    requirement_patterns = [
        r"required skills?[:\-](.*?)(?:preferred|nice to have|responsibilities|requirements|$)",
        r"requirements?[:\-](.*?)(?:preferred|nice to have|responsibilities|$)",
        r"must have[:\-](.*?)(?:preferred|nice to have|$)",
        r"qualifications?[:\-](.*?)(?:preferred|responsibilities|$)"
    ]

    chunks = []

    for pattern in requirement_patterns:
        matches = re.findall(
            pattern,
            t,
            re.S
        )
        chunks.extend(matches)

    if not chunks:
        chunks = [t]

    combined = " ".join(chunks)

    for skill, aliases in SKILL_ALIASES.items():
        if any(
            re.search(
                r"(?<!\w)"
                + re.escape(alias)
                + r"(?!\w)",
                combined
            )
            for alias in aliases
        ):
            required.append(skill)

    return required

def skill_match_score(job, profile):
    candidate_skills = set(
        x.lower()
        for x in extract_job_skills(
            job,
            profile
        )
    )

    job_required = set(
        x.lower()
        for x in required_skills(job)
    )

    if not job_required:
        return 20, [], []

    matched = (
        candidate_skills
        & job_required
    )

    ratio = len(matched) / len(
        job_required
    )

    score = round(
        ratio * 30
    )

    return (
        min(30, score),
        list(matched),
        list(job_required)
    )

def role_score(job):
    groups = matched_roles(job)

    if not groups:
        return 0

    title = job.get(
        "title",
        ""
    ).lower()

    if len(groups) > 1:
        score = 35
    else:
        score = 32

    if "intern" in title:
        score += 2

    return min(
        35,
        score
    )

def domain_fit(job, profile):
    t = text(job)

    score = 0

    if any(
        x in t
        for x in [
            "machine learning",
            "artificial intelligence",
            "computer vision",
            "nlp",
            "deep learning",
            "generative ai",
            "llm"
        ]
    ):
        score += 10

    if any(
        x in t
        for x in [
            "data science",
            "data analysis",
            "data analytics"
        ]
    ):
        score += 5

    return min(
        15,
        score
    )

def location_fit(job, profile):
    location = job.get(
        "location",
        ""
    ).lower()

    preferred = [
        x.lower()
        for x in profile.get(
            "preferred_locations",
            []
        )
    ]

    if job.get(
        "work_mode",
        ""
    ).lower() == "remote":
        return 10

    if any(
        x in location
        for x in preferred
    ):
        return 10

    if "india" in location:
        return 7

    return 3

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
    stipend = stipend_monthly_inr(job)

    if stipend is None:
        return 0

    if stipend >= 50000:
        return 5

    if stipend >= 30000:
        return 4

    return 3

def passes(job, profile):
    if not is_internship(job):
        return False, "Not an internship"

    if blocked_role(
        job,
        profile
    ):
        return False, "Backend-only role"

    if not role_match(
        job,
        profile
    ):
        return False, "Role mismatch"

    if not graduation_ok(
        job,
        profile
    ):
        return False, "Not compatible with 2028 batch"

    if not salary_ok(job):
        return False, "Stipend missing or <= ₹20,000"

    if not duration_ok(
        job,
        profile
    ):
        return False, "Duration not compatible"

    return True, ""

def score(job, profile):
    role_points = role_score(
        job
    )

    skill_points, matched, required = skill_match_score(
        job,
        profile
    )

    domain_points = domain_fit(
        job,
        profile
    )

    location_points = location_fit(
        job,
        profile
    )

    freshness_points = freshness_score(
        job
    )

    stipend_points = stipend_score(
        job
    )

    total = min(
        100,
        role_points
        + skill_points
        + domain_points
        + location_points
        + freshness_points
        + stipend_points
    )

    reasons = []

    groups = matched_roles(job)

    if groups:
        names = {
            "software": "Software Engineering",
            "full_stack": "Full Stack",
            "data_science": "Data Science",
            "data_analyst": "Data Analytics",
            "ml": "Machine Learning",
            "ai": "AI",
            "python": "Python"
        }

        reasons.append(
            "Role: "
            + ", ".join(
                names.get(
                    x,
                    x
                )
                for x in groups
            )
        )

    if matched:
        reasons.append(
            "Your skills matched: "
            + ", ".join(
                matched[:8]
            )
        )

    if required:
        missing = [
            x
            for x in required
            if x not in matched
        ]

        if missing:
            reasons.append(
                "Missing: "
                + ", ".join(
                    missing[:5]
                )
            )

    stipend = stipend_monthly_inr(
        job
    )

    if stipend:
        reasons.append(
            f"Stipend: ₹{int(stipend):,}/month"
        )

    work_mode = job.get(
        "work_mode",
        ""
    ).lower()

    if work_mode:
        reasons.append(
            work_mode.title()
        )

    days = fresh_days(job)

    if days <= 7:
        reasons.append(
            f"Posted {days} day(s) ago"
        )

    return total, reasons

def rank(jobs, profile):
    ranked = []

    for job in jobs:
        ok, reason = passes(
            job,
            profile
        )

        if not ok:
            continue

        job["score"], job["reasons"] = score(
            job,
            profile
        )

        ranked.append(job)

    ranked.sort(
        key=lambda x: (
            x.get(
                "score",
                0
            ),
            -fresh_days(x)
        ),
        reverse=True
    )

    return ranked
