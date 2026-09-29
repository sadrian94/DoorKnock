import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
import jinja2
import typst
from pypdf import PdfReader

import re

logger = logging.getLogger("doorknock.tailor.compiler")

def escape_typst_markup(s: str) -> str:
    """Escape untrusted Typst markup while retaining intentional *bold* spans."""
    # Convert markdown double asterisk **bold** to Typst single asterisk *bold*
    s = re.sub(r'\*\*(.*?)\*\*', r'*\1*', s)
    s = s.replace('\\', '\\\\')
    for char in ('$', '#', '[', ']', '@'):
        s = s.replace(char, f'\\{char}')
    return s

def escape_typst_string(s: str) -> str:
    """Return a quoted Typst string literal, including quote/backslash escapes."""
    return json.dumps(s, ensure_ascii=False)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)
jinja_env.filters["typst_markup"] = escape_typst_markup
jinja_env.filters["typst_string"] = escape_typst_string

def render_typst_template(template_name: str, context: Dict[str, Any]) -> str:
    """Render a .typ.j2 template with the given context dictionary."""
    template = jinja_env.get_template(template_name)
    return template.render(**context)

LAYOUT_PROFILES = [
    {"font_size": "10.5pt", "leading": "0.45em", "spacing": "0.55em", "margin_y": "0.45in", "margin_x": "0.5in"},
    {"font_size": "10.0pt", "leading": "0.42em", "spacing": "0.52em", "margin_y": "0.42in", "margin_x": "0.49in"},
    {"font_size": "9.3pt", "leading": "0.38em", "spacing": "0.48em", "margin_y": "0.38in", "margin_x": "0.48in"},
]

def compile_document(
    template_name: str,
    context: Dict[str, Any],
    output_dir: Path,
    base_filename: str,
    require_single_page: bool = True,
) -> Dict[str, Any]:
    """
    Render Typst template and compile directly into PDF.
    Features automatic 1-page fit optimization for resumes.
    Saves both the .typ source and the .pdf file for transparency.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    typ_path = output_dir / f"{base_filename}.typ"
    pdf_path = output_dir / f"{base_filename}.pdf"

    # Try compact layouts only when the user requires a one-page resume.
    is_resume = template_name.startswith("resume")
    page_limit_required = require_single_page if is_resume else True
    profiles = (
        LAYOUT_PROFILES if require_single_page else [LAYOUT_PROFILES[0]]
    ) if is_resume else [{}]
    last_res: Dict[str, Any] = {}

    for profile in profiles:
        active_context = dict(context)
        if profile:
            active_context["layout"] = profile

        # Step 1: Render Jinja2 to .typ
        rendered_typ = render_typst_template(template_name, active_context)
        typ_path.write_text(rendered_typ, encoding="utf-8")

        # Step 2: Compile with Typst
        try:
            typst.compile(typ_path, output=pdf_path)
        except Exception as e:
            logger.error(f"Typst compilation failed for {typ_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "typ_path": str(typ_path),
                "pdf_path": None,
                "page_count": 0,
                "page_limit_required": page_limit_required,
            }

        # Step 3: Validate generated PDF
        try:
            reader = PdfReader(str(pdf_path))
            page_count = len(reader.pages)
            total_text = "".join([page.extract_text() or "" for page in reader.pages])
            text_chars = len(total_text.strip())
        except Exception as e:
            logger.warning(f"Failed to inspect generated PDF {pdf_path}: {e}")
            page_count = 0
            text_chars = 0
            total_text = ""

        if template_name.startswith("resume"):
            resume = context.get("resume", {})
            required_text = ["Summary"]
            required_text.extend(heading for field, heading in (
                ("experiences", "Experience"), ("skills", "Skills"),
                ("projects", "Projects"), ("education", "Education"),
                ("certifications", "Certifications"),
            ) if resume.get(field))
        else:
            required_text = ["Dear", "Sincerely"]
        text_complete = text_chars >= 100 and all(section.lower() in total_text.lower() for section in required_text)

        last_res = {
            "success": page_count > 0 and (not page_limit_required or page_count == 1) and text_complete,
            "pdf_path": str(pdf_path),
            "typ_path": str(typ_path),
            "page_count": page_count,
            "text_chars": text_chars,
            "text_complete": text_complete,
            "is_single_page": page_count == 1,
            "page_limit_required": page_limit_required,
            "applied_profile": profile,
        }

        # If achieved 1-page fit, stop adjusting
        if last_res["success"]:
            break

    return last_res
