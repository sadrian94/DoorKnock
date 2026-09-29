import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.tailor.compiler import compile_document
from app.tailor.naming import generate_document_filename
from pypdf import PdfReader


def test_resume_and_cover_letter_compilation(tmp_path: Path):
    candidate = {
        "name": "Jane Doe",
        "display_name": "Jane_Doe",
        "headline": "Operations Data Analyst",
        "location": "Sample City",
        "phone": "(555) 019-2834",
        "email": "jane.doe@example.com",
        "linkedin": "example.com/jane-doe",
        "github": "example.com/jane-code",
        "work_authorization": "Authorized to work in the United States",
    }

    resume_context = {
        "candidate": candidate,
        "resume": {
            "target_role": "OPERATIONS DATA ANALYST",
            "summary": (
                "Operations data analyst who builds clear reporting workflows and checks source data before it informs team decisions. "
                "Combines practical SQL and Python skills with experience documenting requirements, validating changes, and explaining results."
            ),
            "experiences": [
                {
                    "company": "Apex Logistics",
                    "location": "Sample City",
                    "title": "Data Operations Analyst",
                    "dates": "2024–2025",
                    "bullets": [
                        "Joined delivery, invoice, and service records with SQL to create a weekly exception report for operations review.",
                        "Built a Python check that flagged missing identifiers and duplicate rows before reports were shared.",
                        "Documented field definitions and review steps so teammates could repeat the reconciliation process.",
                    ],
                },
                {
                    "company": "Sample Services Group",
                    "location": "Sample City",
                    "title": "Project Coordinator",
                    "dates": "2021–2024",
                    "bullets": [
                        "Tracked project milestones and vendor questions in a shared log, escalating schedule risks with supporting notes.",
                        "Collected stakeholder requirements and converted them into acceptance checks for project handoffs.",
                        "Reviewed change requests against approved scope and recorded the decision for later reference.",
                    ],
                },
            ],
            "projects": [
                {
                    "name": "Route Data Quality Study",
                    "tech_stack": "Python | SQLite | Data Validation",
                    "bullets": [
                        "Built a small analysis pipeline that normalized sample route records and reported invalid or incomplete values.",
                        "Compared summary totals with source rows and documented the checks and limits of the sample dataset.",
                    ],
                }
            ],
            "skills": [
                {"category": "Data & Reporting", "items": "SQL, Python, Excel, Power BI, data validation, variance reporting"},
                {"category": "Business Analysis", "items": "Requirements gathering, process mapping, acceptance checks, stakeholder coordination"},
            ],
            "education": [
                {
                    "degree": "Sample Undergraduate Credential",
                    "institution": "Global Tech University",
                    "location": "Sample City",
                    "year": "2024",
                    "focus": "Reporting, statistics, and database fundamentals.",
                }
            ],
            "certifications": "Sample Process Improvement Certificate",
        },
    }

    resume_base = generate_document_filename("resume", "Northstar Sample Industries", candidate_name=candidate["display_name"])
    resume_result = compile_document("resume.typ.j2", resume_context, tmp_path, resume_base)

    assert resume_result["success"], f"Resume compilation failed: {resume_result.get('error')}"
    assert resume_result["is_single_page"], f"Resume exceeded 1 page! Page count: {resume_result['page_count']}"
    assert resume_result["text_chars"] > 1000, f"Resume text extracted was too small: {resume_result['text_chars']}"
    assert Path(resume_result["pdf_path"]).is_file()
    assert candidate["work_authorization"] in PdfReader(resume_result["pdf_path"]).pages[0].extract_text()

    letter_context = {
        "candidate": candidate,
        "letter": {
            "recipient_title": "Hiring Team",
            "company_name": "Northstar Sample Industries",
            "company_location": "Sample City",
            "date": "September 24, 2026",
            "subject_role": "Operations Data Analyst",
            "salutation": "Northstar Sample Industries Hiring Team",
            "paragraphs": [
                "I am applying for the Operations Data Analyst role because the work combines reporting, data checks, and clear handoffs. In a synthetic operations example, I used SQL to join delivery and invoice records, then built a weekly exception view for review. I would bring the same careful approach to understanding your reporting needs.",
                "I also wrote a small Python validation step to flag missing identifiers and duplicate rows before a report was shared. I documented the inputs and checks so another teammate could repeat the process. In project coordination work, I gathered requirements, tracked decisions, and translated handoff needs into acceptance checks.",
                "My portfolio study of route records gave me another chance to compare summary totals against source rows and describe the limits of a sample dataset. I would welcome a conversation about the reports this role owns and how your team checks data quality. Thank you for your consideration.",
            ],
        },
    }

    letter_base = generate_document_filename("cover_letter", "Northstar Sample Industries", candidate_name=candidate["display_name"])
    letter_result = compile_document("cover_letter.typ.j2", letter_context, tmp_path, letter_base)

    assert letter_result["success"], f"Cover letter compilation failed: {letter_result.get('error')}"
    assert letter_result["is_single_page"], f"Cover letter exceeded 1 page! Page count: {letter_result['page_count']}"
    assert letter_result["text_chars"] > 500, f"Cover letter text extracted was too small: {letter_result['text_chars']}"
    assert Path(letter_result["pdf_path"]).is_file()
    assert candidate["work_authorization"] not in PdfReader(letter_result["pdf_path"]).pages[0].extract_text()
