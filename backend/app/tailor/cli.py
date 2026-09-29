import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add backend directory to sys.path if invoked directly
BASE_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import crud
from app.tailor.engine import tailor_application_documents

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

async def run_cli():
    parser = argparse.ArgumentParser(description="DoorKnock Document Tailor CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--job-id", type=str, help="Target Job ID from DoorKnock database")
    group.add_argument("--jd-file", type=str, help="Path to raw JD text file")

    parser.add_argument("--company", type=str, default="", help="Company name (if using --jd-file)")
    parser.add_argument("--title", type=str, default="", help="Job title (if using --jd-file)")
    parser.add_argument("--location", type=str, default="Remote/Hybrid", help="Job location")
    parser.add_argument("--document-type", choices=("resume", "cover_letter"), required=True)
    parser.add_argument("--authored-json", type=Path, required=True,
                        help="Agent-authored JSON for the selected document; CLI never calls the AI provider")

    args = parser.parse_args()

    if args.job_id:
        job = crud.get_job_by_id(args.job_id)
        if not job:
            print(f"Error: Job with ID '{args.job_id}' not found in DoorKnock database.", file=sys.stderr)
            sys.exit(1)
        job_data = job
    else:
        jd_path = Path(args.jd_file)
        if not jd_path.is_file():
            print(f"Error: JD file '{args.jd_file}' not found.", file=sys.stderr)
            sys.exit(1)
        raw_text = jd_path.read_text(encoding="utf-8")
        job_data = {
            "title": args.title or "Job Candidate",
            "company": args.company or "Company",
            "location": args.location,
            "raw_text": raw_text,
            "job_brief": raw_text[:400],
        }

    print(f"Tailoring {args.document_type} for {job_data.get('title')} at {job_data.get('company')}...")
    authored_documents = json.loads(args.authored_json.read_text(encoding="utf-8"))
    res = await tailor_application_documents(job_data, document_type=args.document_type,
                                             authored_documents=authored_documents)

    if not res.get("success"):
        print("Error: Document tailoring or Typst compilation failed.", file=sys.stderr)
        sys.exit(1)

    manifest = res.get("manifest", {})
    strategy = manifest.get("tailor_strategy", {})
    print("\n" + "="*60)
    print("Document Successfully Tailored & Compiled")
    print("="*60)
    print(f"Target Role: {strategy.get('target_role_header')}")
    print(f"Hook Strategy: {strategy.get('primary_angle')}")
    print(f"\nArtifacts Directory: {res.get('application_dir')}")
    print(f"Document type: {args.document_type}")
    print(f"PDF: {res.get('pdf')}")
    print("="*60 + "\n")

def main():
    asyncio.run(run_cli())

if __name__ == "__main__":
    main()
