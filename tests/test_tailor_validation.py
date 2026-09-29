import pytest

from app.tailor.compiler import LAYOUT_PROFILES
from app.tailor.validation import validate_resume_evidence


EVIDENCE = """experiences:
  - company: Apex Logistics
    role: Operations Analyst
    dates: 2024-2025
    location: Sample City
    bullets:
      - text: Improved reporting for 12 teams.
education:
  - institution: Sample University
    degree: BS Analytics
    year: 2023
    location: Sample City
projects: []
"""


def test_resume_layout_never_shrinks_below_readable_floor():
    assert min(float(profile["font_size"].removesuffix("pt")) for profile in LAYOUT_PROFILES) >= 9.3


def test_supported_exact_facts_pass():
    resume = {"summary": "Operations reporting", "experiences": [
        {"company": "Apex Logistics", "title": "Operations Analyst", "dates": "2024-2025",
         "location": "Sample City", "bullets": ["Improved reporting for 12 teams."]}],
        "education": [{"institution": "Sample University", "degree": "BS Analytics",
                       "year": 2023, "location": "Sample City"}],
        "projects": [], "certifications": ""}
    validate_resume_evidence(resume, EVIDENCE)


@pytest.mark.parametrize("change", [
    {"company": "Other Company"},
    {"title": "Senior Operations Analyst"},
    {"dates": "2020-2025"},
    {"bullets": ["Improved reporting for 40 teams."]},
])
def test_unsupported_facts_stop_publication(change):
    resume = {"summary": "Operations reporting", "experiences": [
        {"company": "Apex Logistics", "title": "Operations Analyst", "dates": "2024-2025",
         "location": "Sample City", "bullets": ["Improved reporting for 12 teams."]} | change],
        "education": [], "projects": [], "certifications": ""}
    with pytest.raises(ValueError):
        validate_resume_evidence(resume, EVIDENCE)


def test_multiple_degrees_at_same_institution_pass():
    multi_edu_evidence = """experiences: []
education:
  - institution: Example Tech University
    degree: Master of Science, Systems Engineering
    year: 2025
    location: Example City, EX
  - institution: Example Tech University
    degree: Bachelor of Science, Applied Analytics
    year: 2023
    location: Example City, EX
projects: []
"""
    resume = {
        "summary": "Operations reporting",
        "experiences": [],
        "education": [
            {
                "institution": "Example Tech University",
                "degree": "Master of Science, Systems Engineering",
                "year": 2025,
                "location": "Example City, EX",
            },
            {
                "institution": "Example Tech University",
                "degree": "Bachelor of Science, Applied Analytics",
                "year": 2023,
                "location": "Example City, EX",
            },
        ],
        "projects": [],
        "certifications": "",
    }
    validate_resume_evidence(resume, multi_edu_evidence)

