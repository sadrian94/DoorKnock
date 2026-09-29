import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from .config import APPLICATIONS_DIR, WORKSPACE_DIR
from . import crud

def _normalize_version_key(v: str) -> int:
    """Extract numeric value for sorting version strings like 'v001', 'v010'."""
    match = re.search(r'\d+', v)
    return int(match.group()) if match else 0

def _get_file_info(file_path: Path, version_str: str) -> Dict[str, Any]:
    stat = file_path.stat()
    updated_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    return {
        "version": version_str,
        "filename": file_path.name,
        "size_bytes": stat.st_size,
        "updated_at": updated_at,
        "file_path": str(file_path),
    }

def find_application_directory(job_id: str) -> Optional[Path]:
    """
    Search DoorKnock/workspace/applications for a folder matching job_id or source_job_id.
    """
    job = crud.get_job_by_id(job_id)
    source_job_id = job.get("source_job_id") if job else None
    company = job.get("company", "").strip().lower() if job else ""
    title = job.get("title", "").strip().lower() if job else ""

    search_dirs = [APPLICATIONS_DIR]

    # Pass 1: Direct directory name match
    for base_dir in search_dirs:
        if not base_dir.exists():
            continue
        direct_path = base_dir / job_id
        if direct_path.is_dir():
            return direct_path
        if source_job_id:
            source_path = base_dir / source_job_id
            if source_path.is_dir():
                return source_path

    # Pass 2: Inspect metadata in each subdirectory
    metadata_matches = []
    for base_dir in search_dirs:
        if not base_dir.exists():
            continue
        for sub in base_dir.iterdir():
            if not sub.is_dir():
                continue

            # Check workspace-metadata.json
            meta_path = sub / "workspace-metadata.json"
            if meta_path.is_file():
                try:
                    data = json.loads(meta_path.read_text(encoding="utf-8"))
                    meta_jid = data.get("job_id")
                    if meta_jid and (meta_jid == job_id or (source_job_id and meta_jid == source_job_id)):
                        metadata_matches.append(sub)
                except Exception:
                    pass

            # Check job-snapshot.json
            snap_path = sub / "job-snapshot.json"
            if snap_path.is_file():
                try:
                    sdata = json.loads(snap_path.read_text(encoding="utf-8"))
                    snap_jid = sdata.get("job_id") or sdata.get("job", {}).get("id")
                    if snap_jid and (snap_jid == job_id or (source_job_id and snap_jid == source_job_id)):
                        metadata_matches.append(sub)
                except Exception:
                    pass

    if metadata_matches:
        return max(metadata_matches, key=lambda path: path.stat().st_mtime)

    # Pass 3: Fuzzy matching on company & title in directory name
    if company:
        comp_slug = re.sub(r'[^a-z0-9]+', '', company)
        title_slug = re.sub(r'[^a-z0-9]+', '', title)[:15] if title else ""
        for base_dir in search_dirs:
            if not base_dir.exists():
                continue
            for sub in base_dir.iterdir():
                if not sub.is_dir():
                    continue
                metadata_path = sub / "workspace-metadata.json"
                if metadata_path.is_file():
                    # Do not associate a different job's published documents by name alone.
                    continue
                clean_name = re.sub(r'[^a-z0-9]+', '', sub.name.lower())
                if comp_slug and comp_slug in clean_name:
                    if not title_slug or title_slug in clean_name:
                        return sub

    return None

def scan_document_versions(app_dir: Path, doc_type: str) -> Dict[str, Any]:
    """
    Scans for resume or cover-letter versions inside an application directory.
    doc_type: 'resume' or 'cover_letter'
    """
    sub_folder_name = "resume" if doc_type == "resume" else "cover-letter"
    target_dir = app_dir / sub_folder_name
    versions: List[Dict[str, Any]] = []

    # Read previously published paired versions as well as independent versions.
    versions_dir = app_dir / "versions"
    if versions_dir.is_dir():
        for version_dir in versions_dir.iterdir():
            if not version_dir.is_dir() or not re.fullmatch(r"v\d+", version_dir.name):
                continue
            document_dir = version_dir / sub_folder_name
            pdfs = sorted(document_dir.glob("*.pdf")) if document_dir.is_dir() else []
            if len(pdfs) == 1:
                versions.append(_get_file_info(pdfs[0], version_dir.name))

    if target_dir.is_dir():
        # Check vXXX subdirectories
        v_dirs = [d for d in target_dir.iterdir() if d.is_dir() and re.fullmatch(r'v\d+', d.name)]
        # Sort by version number ascending
        v_dirs.sort(key=lambda d: _normalize_version_key(d.name))

        for vd in v_dirs:
            # Look for final.pdf or letter.pdf or source.pdf or any .pdf
            pdf_candidates = [
                vd / "final.pdf",
                vd / "letter.pdf",
                vd / "source.pdf",
            ]
            chosen_pdf: Optional[Path] = None
            for cand in pdf_candidates:
                if cand.is_file():
                    chosen_pdf = cand
                    break
            if not chosen_pdf:
                other_pdfs = list(vd.glob("*.pdf"))
                if other_pdfs:
                    chosen_pdf = other_pdfs[0]

            if chosen_pdf:
                versions.append(_get_file_info(chosen_pdf, vd.name))

        # Direct final.pdf in resume/ or cover-letter/
        direct_final = target_dir / "final.pdf"
        if direct_final.is_file() and not any(v["filename"] == direct_final.name for v in versions):
            versions.append(_get_file_info(direct_final, "latest"))

    # Also check root of app_dir for e.g. BDO_Extraction_Solutions_Assoc_Resume.pdf
    marker = "resume" if doc_type == "resume" else "cover"
    root_candidates = [path for path in app_dir.iterdir()
                       if path.is_file() and path.suffix.lower() == ".pdf" and marker in path.name.lower()]
    if root_candidates and not any(v["version"] == "v001" for v in versions):
        versions.append(_get_file_info(max(root_candidates, key=lambda path: path.stat().st_mtime), "v001"))

    # If a legacy and a new version share a number, prefer the new per-document path.
    versions = list({entry["version"]: entry for entry in versions}.values())
    # Sort versions descending so latest is first
    versions.sort(key=lambda v: _normalize_version_key(v["version"]), reverse=True)

    available = len(versions) > 0
    latest_version = versions[0]["version"] if available else None

    # Attach download_filename to each version
    for v in versions:
        v["download_filename"] = generate_download_filename(app_dir.name, doc_type, v["version"])

    return {
        "available": available,
        "latest_version": latest_version,
        "download_filename": generate_download_filename(app_dir.name, doc_type, latest_version) if available else None,
        "versions": versions,
    }

def get_candidate_name() -> str:
    """Read preferred or full name from profile.yaml / profile.json or fallback to Candidate."""
    profile_paths = [WORKSPACE_DIR / "profile.yaml", WORKSPACE_DIR / "profile.json"]
    for p in profile_paths:
        if p.is_file():
            try:
                content = p.read_text(encoding="utf-8")
                pref_match = re.search(r'preferred_name:\s*["\']?([^"\'\r\n]+)["\']?', content)
                if pref_match and pref_match.group(1).strip():
                    return re.sub(r'[^a-zA-Z0-9]+', '_', pref_match.group(1).strip()).strip('_')
                full_match = re.search(r'full_name:\s*["\']?([^"\'\r\n]+)["\']?', content)
                if full_match and full_match.group(1).strip():
                    return re.sub(r'[^a-zA-Z0-9]+', '_', full_match.group(1).strip()).strip('_')
            except Exception:
                pass
    return "Candidate"

def generate_download_filename(job_id_or_app_name: str, doc_type: str, version: Optional[str] = None) -> str:
    """
    Generate clean, ATS-optimized filename instead of generic final.pdf.
    Example: [Candidate_Name]_Resume_[Company].pdf
    """
    candidate_name = get_candidate_name()
    doc_label = "Resume" if doc_type == "resume" else "Cover_Letter"

    job = crud.get_job_by_id(job_id_or_app_name)
    company_part = ""
    if job and job.get("company"):
        raw_comp = job["company"].strip()
        clean_comp = re.sub(r'[^a-zA-Z0-9]+', '_', raw_comp).strip('_')
        if clean_comp:
            company_part = f"_{clean_comp}"

    version_part = ""
    if version and version.lower() not in ["latest", "final"]:
        version_part = f"_{version}"

    return f"{candidate_name}_{doc_label}{company_part}{version_part}.pdf"

def get_job_documents_info(job_id: str) -> Dict[str, Any]:
    """Retrieve metadata about available resume and cover letter documents for a job."""
    app_dir = find_application_directory(job_id)
    if not app_dir:
        return {
            "job_id": job_id,
            "has_documents": False,
            "application_dir": None,
            "resume": {"available": False, "latest_version": None, "download_filename": None, "versions": []},
            "cover_letter": {"available": False, "latest_version": None, "download_filename": None, "versions": []},
        }

    resume_info = scan_document_versions(app_dir, "resume")
    cover_letter_info = scan_document_versions(app_dir, "cover_letter")

    # Ensure download_filename is enriched with actual job metadata
    if resume_info["available"]:
        resume_info["download_filename"] = generate_download_filename(job_id, "resume", resume_info["latest_version"])
        for v in resume_info["versions"]:
            v["download_filename"] = generate_download_filename(job_id, "resume", v["version"])

    if cover_letter_info["available"]:
        cover_letter_info["download_filename"] = generate_download_filename(job_id, "cover_letter", cover_letter_info["latest_version"])
        for v in cover_letter_info["versions"]:
            v["download_filename"] = generate_download_filename(job_id, "cover_letter", v["version"])

    return {
        "job_id": job_id,
        "has_documents": resume_info["available"] or cover_letter_info["available"],
        "application_dir": app_dir.name,
        "resume": resume_info,
        "cover_letter": cover_letter_info,
    }

def resolve_document_file_path(job_id: str, doc_type: str, version: Optional[str] = None) -> Optional[Path]:
    """
    Resolve and validate absolute path to requested PDF file.
    Ensures safe path traversal checking.
    """
    normalized_doc = "resume" if doc_type == "resume" else "cover_letter"
    info = get_job_documents_info(job_id)
    doc_info = info.get(normalized_doc)
    if not doc_info or not doc_info.get("available"):
        return None

    versions = doc_info.get("versions", [])
    if not versions:
        return None

    target_version_entry = None
    if version:
        for v in versions:
            if v["version"] == version:
                target_version_entry = v
                break

    if version and not target_version_entry:
        return None

    # If no version was requested, use latest (first item).
    if not target_version_entry:
        target_version_entry = versions[0]

    file_path = Path(target_version_entry["file_path"]).resolve()

    # Security check: resolved files must remain inside DoorKnock's private workspace.
    allowed_roots = [WORKSPACE_DIR.resolve()]
    is_safe = False
    for root in allowed_roots:
        try:
            file_path.relative_to(root)
            is_safe = True
            break
        except ValueError:
            continue

    if not is_safe or not file_path.is_file():
        return None

    return file_path
