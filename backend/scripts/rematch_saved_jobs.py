import asyncio
import json
import sqlite3
from pathlib import Path
import sys

# Ensure backend directory is in python path
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app.config import DOORKNOCK_DB_PATH
from app.clock import utc_now
from app.ai.provider import get_ai_client
from app.ai.analyzer import analyze_job_posting

async def rematch_all_saved_jobs():
    print("=" * 60)
    print("🚀 Re-matching all jobs in 'saved' stage with V2 Tactical Brief...")
    print("=" * 60)

    client = get_ai_client()
    if not client.is_configured():
        print("Error: GEMINI_API_KEY is not configured in .env", file=sys.stderr)
        return

    conn = sqlite3.connect(DOORKNOCK_DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT j.id, j.title, j.company, j.job_description, j.company_url, j.job_url
        FROM jobs j
        LEFT JOIN applications a ON j.id = a.job_id
        WHERE a.current_stage = ? OR j.status = ?
        ORDER BY j.created_at ASC
    """, ("saved", "saved"))
    saved_jobs = cur.fetchall()

    print(f"Found {len(saved_jobs)} saved jobs to rematch.\n")

    for i, row in enumerate(saved_jobs, start=1):
        job_id, title, company, jd_text, company_url, job_url = row
        print(f"[{i}/{len(saved_jobs)}] Rematching: {title} @ {company}...")

        if not jd_text or len(jd_text.strip()) < 30:
            print(f"  ⚠️ Skipping {job_id}: JD text too short or missing.\n")
            continue

        try:
            analysis = await analyze_job_posting(
                raw_text=jd_text,
                source_url=company_url or job_url,
                gemini_client=client
            )
        except Exception as e:
            print(f"  ❌ Analysis failed for {title} @ {company}: {e}\n")
            continue

        score = analysis.get("suitability_score")
        reason = analysis.get("suitability_reason")
        analysis_str = json.dumps(analysis, ensure_ascii=False)
        now_str = utc_now().isoformat()

        cur.execute("""
            UPDATE jobs
            SET suitability_score = ?,
                suitability_reason = ?,
                analysis_json = ?,
                updated_at = ?
            WHERE id = ?
        """, (score, reason, analysis_str, now_str, job_id))
        conn.commit()

        triage = analysis.get("triage", {})
        decision = triage.get("decision", "N/A")
        thesis = triage.get("strategic_thesis", "")
        print(f"  ✅ Complete! Verdict: {decision} ({score}%)")
        print(f"     Thesis: {thesis[:120]}...\n")

    conn.close()
    print("=" * 60)
    print("✨ All saved jobs have been successfully rematched with V2 Tactical Brief!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(rematch_all_saved_jobs())
