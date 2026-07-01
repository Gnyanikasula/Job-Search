"""
scrapers/scrape_worker.py
Standalone worker that runs ONE jobspy scrape in an isolated process.

Why: jobspy uses pandas/numpy. On some machines numpy is a broken build that
CRASHES the whole process at the C level (no Python traceback). Running the
scrape in a separate process means such a crash kills only this worker — the
FastAPI server stays alive and simply gets an empty result for that site.

Protocol:
  - Reads a JSON object from stdin: {site, search_term, location,
    results_wanted, hours_old, country_indeed}
  - Writes exactly one line to stdout: the marker ###RESULT### followed by
    a JSON object {ok: bool, jobs: [...], error: str}
  - All library noise goes to stderr and is ignored by the parent.
"""
import sys
import json
import warnings

warnings.filterwarnings("ignore")

MARKER = "###RESULT###"


def _safe_str(v) -> str:
    if v is None:
        return ""
    s = str(v)
    return "" if s.lower() == "nan" else s


def main():
    try:
        args = json.loads(sys.stdin.read())
    except Exception as e:
        sys.stdout.write(MARKER + json.dumps({"ok": False, "jobs": [], "error": f"bad args: {e}"}))
        return

    try:
        from jobspy import scrape_jobs
        df = scrape_jobs(
            site_name=[args["site"]],
            search_term=args["search_term"],
            location=args["location"],
            results_wanted=args.get("results_wanted", 20),
            hours_old=args.get("hours_old", 72),
            country_indeed=args.get("country_indeed", "UK"),
            linkedin_fetch_description=False,
            verbose=0,
        )
        jobs = []
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                jobs.append({
                    "title":       _safe_str(row.get("title")),
                    "company":     _safe_str(row.get("company")),
                    "location":    _safe_str(row.get("location")),
                    "source":      _safe_str(row.get("site")),
                    "job_url":     _safe_str(row.get("job_url")),
                    "description": _safe_str(row.get("description"))[:3000],
                    "date_posted": _safe_str(row.get("date_posted")),
                })
        sys.stdout.write(MARKER + json.dumps({"ok": True, "jobs": jobs, "error": ""}))
    except Exception as e:
        sys.stdout.write(MARKER + json.dumps({"ok": False, "jobs": [], "error": str(e)}))


if __name__ == "__main__":
    main()
