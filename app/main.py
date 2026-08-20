import json
from pathlib import Path

from sources import fetch_all
from filter import rank
from telegram import send, build

ROOT = Path(__file__).resolve().parents[1]

MIN_SCORE = 65
MAX_JOBS = 20

def load_profile():
    return json.loads(
        (ROOT / "profile" / "candidate.json").read_text(
            encoding="utf-8"
        )
    )

def load_seen():
    path = ROOT / "data" / "seen.json"

    if not path.exists():
        return {}

    return json.loads(
        path.read_text(encoding="utf-8")
    )

def save_seen(seen):
    path = ROOT / "data" / "seen.json"

    path.write_text(
        json.dumps(
            seen,
            indent=2
        ),
        encoding="utf-8"
    )

def main():
    profile = load_profile()
    seen = load_seen()

    jobs = fetch_all()

    new_jobs = [
        job
        for job in jobs
        if job.get("id") not in seen
    ]

    ranked = rank(
        new_jobs,
        profile
    )

    qualified = [
        job
        for job in ranked
        if job.get("score", 0) >= MIN_SCORE
    ]

    top = qualified[:MAX_JOBS]

    for job in jobs:
        job_id = job.get("id")

        if job_id:
            seen[job_id] = job.get(
                "created",
                ""
            )

    save_seen(seen)

    print(f"Fetched: {len(jobs)}")
    print(f"New: {len(new_jobs)}")
    print(f"Passed hard filters: {len(ranked)}")
    print(f"Score >= {MIN_SCORE}: {len(qualified)}")
    print(f"Selected: {len(top)}")

    if ranked:
        print(
            "Top scores:",
            [
                job.get("score", 0)
                for job in ranked[:10]
            ]
        )

    if not top:
        send(
            "<b>Daily Internship Search</b>\n\n"
            f"No new internships matched the hard filters "
            f"and reached the minimum match score of {MIN_SCORE}/100."
        )
        return

    send(build(top))

if __name__ == "__main__":
    main()
