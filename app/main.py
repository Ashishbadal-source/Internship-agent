import json
from pathlib import Path

from sources import fetch_all
from filter import rank, passes
from telegram import send, build

ROOT = Path(__file__).resolve().parents[1]

MIN_SCORE = 65
MAX_JOBS = 20

def load_profile():
    return json.loads(
        (
            ROOT
            / "profile"
            / "candidate.json"
        ).read_text(
            encoding="utf-8"
        )
    )

def load_seen():
    path = (
        ROOT
        / "data"
        / "seen.json"
    )

    if not path.exists():
        return {}

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

def save_seen(seen):
    path = (
        ROOT
        / "data"
        / "seen.json"
    )

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
        if job.get("id")
        not in seen
    ]

    hard_pass = []
    rejection_counts = {}

    for job in new_jobs:
        ok, reason = passes(
            job,
            profile
        )

        if ok:
            hard_pass.append(job)
        else:
            rejection_counts[reason] = (
                rejection_counts.get(
                    reason,
                    0
                ) + 1
            )

    ranked = rank(
        hard_pass,
        profile
    )

    qualified = [
        job
        for job in ranked
        if job.get(
            "score",
            0
        ) >= MIN_SCORE
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

    print(
        f"Fetched: {len(jobs)}"
    )

    print(
        f"New: {len(new_jobs)}"
    )

    print(
        f"Passed hard filters: {len(hard_pass)}"
    )

    print(
        f"Score >= {MIN_SCORE}: "
        f"{len(qualified)}"
    )

    print(
        f"Selected: {len(top)}"
    )

    if ranked:
        print(
            "Top scores:",
            [
                job.get(
                    "score",
                    0
                )
                for job in ranked[:10]
            ]
        )

    if rejection_counts:
        print(
            "Rejections:"
        )

        for reason, count in sorted(
            rejection_counts.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(
                f"  {reason}: {count}"
            )

    if not top:
        send(
            "<b>Daily Internship Search</b>\n\n"
            f"No new internships matched your "
            f"requirements with a score of "
            f"{MIN_SCORE}/100 or higher."
        )
        return

    send(
        build(top)
    )

if __name__ == "__main__":
    main()
