import json
from pathlib import Path
from sources import fetch_all
from filter import rank
from telegram import send, build

ROOT = Path(__file__).resolve().parents[1]

def load_profile():
    return json.loads((ROOT / "profile" / "candidate.json").read_text(encoding="utf-8"))

def load_seen():
    path = ROOT / "data" / "seen.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def save_seen(seen):
    path = ROOT / "data" / "seen.json"
    path.write_text(json.dumps(seen, indent=2), encoding="utf-8")

def main():
    profile = load_profile()
    seen = load_seen()
    jobs = fetch_all()
    new_jobs = [x for x in jobs if x.get("id") not in seen]
    ranked = rank(new_jobs, profile)

    top = [
        job for job in ranked
        if job.get("score", 0) >= 65
    ][:20]

    for job in jobs:
        seen[job.get("id")] = job.get("created", "")

    save_seen(seen)

    if not top:
        send(
            "<b>Daily Internship Search</b>\n\n"
            "No new internships with a match score of 65+ today."
        )
        return

    send(build(top))

    print(f"Fetched: {len(jobs)}")
    print(f"New: {len(new_jobs)}")
    print(f"Selected: {len(top)}")

if __name__ == "__main__":
    main()
