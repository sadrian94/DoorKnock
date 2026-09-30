import re
from ..clock import local_today
from pathlib import Path
from typing import Optional

def sanitize_slug(text: str, max_len: int = 50) -> str:
    """Clean string for directory and file naming: lowercase, alphanumeric and hyphens."""
    s = text.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:max_len]

def sanitize_title_case(text: str, max_len: int = 40) -> str:
    """Clean string for file names: e.g. 'Brinkmann_Constructors'."""
    words = re.findall(r'[a-zA-Z0-9]+', text)
    if not words:
        return "Company"
    capitalized = [w.capitalize() if not w.isupper() else w for w in words]
    return "_".join(capitalized)[:max_len]

def get_candidate_display_name(raw_name: Optional[str] = None) -> str:
    if raw_name:
        words = re.findall(r'[a-zA-Z0-9]+', raw_name)
        if words:
            return "_".join(words)
    return "Candidate"

def generate_document_filename(
    doc_type: str, # 'resume' or 'cover_letter'
    company: str,
    candidate_name: str = "Candidate",
    version: Optional[str] = None,
) -> str:
    """
    Format: [Candidate_Name]_Resume_[Company].pdf
    Or: [Candidate_Name]_Cover_Letter_[Company].pdf
    """
    doc_label = "Resume" if doc_type == "resume" else "Cover_Letter"
    company_clean = sanitize_title_case(company)
    version_part = f"_{version}" if version and version.lower() not in ["latest", "v001"] else ""
    return f"{candidate_name}_{doc_label}_{company_clean}{version_part}"

def generate_application_workspace_dirname(
    company: str,
    title: str,
    date_str: Optional[str] = None,
) -> str:
    """
    Format: YYYY-MM-DD-company-position
    e.g.: 2026-09-18-brinkmann-constructors-data-analyst
    """
    d = date_str or local_today().isoformat()
    comp_slug = sanitize_slug(company, max_len=30) or "company"
    title_slug = sanitize_slug(title, max_len=35) or "job"
    return f"{d}-{comp_slug}-{title_slug}"
