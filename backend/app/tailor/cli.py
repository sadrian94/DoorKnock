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
from app.config import APPLICATIONS_DIR
from app.tailor.engine import tailor_application_documents, publish_reviewed_preview

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

async def run_cli():
    parser = argparse.ArgumentParser(description="DoorKnock Document Tailor CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--job-id", type=str, help="Target Job ID from DoorKnock database")
    group.add_argument("--jd-file", type=str, help="Path to raw JD text file")
    group.add_argument("--publish-preview", type=Path, help="Publish a visually reviewed preview directory")

    parser.add_argument("--company", type=str, default="", help="Company name (if using --jd-file)")
    parser.add_argument("--title", type=str, default="", help="Job title (if using --jd-file)")
    parser.add_argument("--location", type=str, default="Remote/Hybrid", help="Job location")
    parser.add_argument("--document-type", choices=("resume", "cover_letter"))
    parser.add_argument("--authored-json", type=Path,
                        help="Agent-authored JSON for the selected document; CLI never calls the AI provider")
    parser.add_argument("--preview-only", action="store_true", help="Create an unpublished preview")
    parser.add_argument("--reviewed-pdf-sha256", help="SHA256 of the exact visually reviewed preview PDF")

    args = parser.parse_args()

    if args.publish_preview:
        if args.preview_only or args.authored_json or args.document_type or not args.reviewed_pdf_sha256:
            parser.error("--publish-preview requires --reviewed-pdf-sha256 and no authoring options")
        preview = args.publish_preview
        try:
            preview.resolve().relative_to(APPLICATIONS_DIR.resolve())
            res = publish_reviewed_preview(preview, args.reviewed_pdf_sha256)
        except (ValueError, OSError, KeyError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if not args.document_type or not args.authored_json:
        parser.error("--document-type and --authored-json are required for authoring")
    if args.reviewed_pdf_sha256:
        parser.error("--reviewed-pdf-sha256 is only valid with --publish-preview")

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
                                             authored_documents=authored_documents, preview_only=args.preview_only)

    if not res.get("success"):
        print("Error: " + res.get("error", "Document tailoring or Typst compilation failed."), file=sys.stderr)
        for finding in (res.get("keyword_review", {}).get("claim_review", {}).get("findings", [])):
            print(f"{finding['section']}: {finding['issue']} — {finding['suggestion']}", file=sys.stderr)
        sys.exit(1)

    if args.preview_only:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
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
    print(f"Keyword review: {manifest.get('keyword_review')}")
    print(f"Alignment status: {manifest.get('alignment_status')}")
    print("="*60 + "\n")

def main():
    asyncio.run(run_cli())

if __name__ == "__main__":
    main()
