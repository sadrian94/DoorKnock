import json
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from app.tailor import compiler, engine
from app.documents import scan_document_versions


class FakeClient:
    def __init__(self):
        self.prompts = []

    async def generate_json(self, **kwargs):
        prompt = kwargs["prompt"]
        self.prompts.append(prompt)
        if "Write only the resume Experience and Projects" in prompt:
            return {"experiences": [], "projects": []}
        if "Write only resume Skills, Education" in prompt:
            return {"skills": [], "education": [], "certifications": ""}
        if "Write only the resume Summary" in prompt:
            return {"summary": "Synthetic summary"}
        if "cover letter" in prompt.lower():
            return {"paragraphs": ["Synthetic letter"]}
        return {"target_role_header": "ANALYST", "primary_angle": "Synthetic fit"}


class MissingSummaryClient(FakeClient):
    async def generate_json(self, **kwargs):
        if "Write only the resume Summary" in kwargs["prompt"]:
            return {}
        return await super().generate_json(**kwargs)


class ForbiddenClient:
    async def generate_json(self, **_kwargs):
        raise AssertionError("Agent-authored path must not call Gemini")


@pytest.fixture
def synthetic_candidate(monkeypatch):
    monkeypatch.setattr(engine, "load_candidate_base_context", lambda: {
        "candidate": {"name": "Alex Taylor", "display_name": "Alex_Taylor", "headline": "Analyst",
                      "location": "Remote", "phone": "(555) 019-2834", "email": "alex@example.com",
                      "linkedin": "example.com/profile", "github": "example.com/code",
                      "work_authorization": "Authorized", "projects_meta": []},
        "candidate_evidence_context": "experiences: []\nprojects: []\neducation: []\ncertifications: {}",
    })


@pytest.mark.anyio
async def test_retailor_publishes_distinct_versions(tmp_path, monkeypatch, synthetic_candidate):
    def fake_compile(_template, _context, output_dir, base_filename, **_kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf = output_dir / f"{base_filename}.pdf"
        typ = output_dir / f"{base_filename}.typ"
        pdf.write_bytes(b"synthetic pdf")
        typ.write_text("synthetic typst", encoding="utf-8")
        return {"success": True, "is_single_page": True, "pdf_path": str(pdf), "typ_path": str(typ)}

    monkeypatch.setattr(engine, "compile_document", fake_compile)
    job = {"id": "synthetic-job", "company": "Apex Logistics", "title": "Analyst", "raw_text": "Analyze data"}
    client = FakeClient()
    first = await engine.tailor_application_documents(job, custom_output_dir=tmp_path, gemini_client=client)
    second = await engine.tailor_application_documents(job, custom_output_dir=tmp_path, gemini_client=FakeClient())
    letter_client = FakeClient()
    letter = await engine.tailor_application_documents(job, document_type="cover_letter",
        custom_output_dir=tmp_path, gemini_client=letter_client)

    assert first["success"] and second["success"] and letter["success"]
    assert len(client.prompts) == 4
    assert len(letter_client.prompts) == 1
    assert "Selected resume:" in client.prompts[3]
    assert first["manifest"]["version"] == "v001"
    assert second["manifest"]["version"] == "v002"
    assert letter["manifest"]["version"] == "v001"
    assert Path(first["pdf"]).read_bytes() == b"synthetic pdf"
    assert Path(second["pdf"]).parent == tmp_path / "resume" / "v002"
    assert Path(letter["pdf"]).parent == tmp_path / "cover-letter" / "v001"
    assert [v["version"] for v in scan_document_versions(tmp_path, "resume")["versions"]] == ["v002", "v001"]
    assert [v["version"] for v in scan_document_versions(tmp_path, "cover_letter")["versions"]] == ["v001"]
    latest = json.loads((tmp_path / "workspace-metadata.json").read_text(encoding="utf-8"))
    assert latest["documents"]["resume"]["version"] == "v002"
    assert latest["documents"]["cover_letter"]["version"] == "v001"


@pytest.mark.anyio
async def test_failed_retailor_keeps_previous_version(tmp_path, monkeypatch, synthetic_candidate):
    def fake_compile(template, _context, output_dir, base_filename, **_kwargs):
        if template.startswith("cover"):
            return {"success": False, "is_single_page": False, "pdf_path": None, "typ_path": None}
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf = output_dir / f"{base_filename}.pdf"
        pdf.write_bytes(b"synthetic pdf")
        return {"success": True, "is_single_page": True, "pdf_path": str(pdf), "typ_path": None}

    monkeypatch.setattr(engine, "compile_document", fake_compile)
    job = {"id": "synthetic-job", "company": "Apex Logistics", "title": "Analyst", "raw_text": "Analyze data"}
    result = await engine.tailor_application_documents(job, document_type="cover_letter",
        custom_output_dir=tmp_path, gemini_client=FakeClient())
    assert not result["success"]
    assert not (tmp_path / "cover-letter" / "v001").exists()
    assert not (tmp_path / "workspace-metadata.json").exists()


@pytest.mark.anyio
async def test_missing_summary_stops_publication(tmp_path, synthetic_candidate):
    job = {"id": "synthetic-job", "company": "Apex Logistics", "title": "Analyst", "raw_text": "Analyze data"}
    with pytest.raises(ValueError, match="missing fields: summary"):
        await engine.tailor_application_documents(job, custom_output_dir=tmp_path,
                                                  gemini_client=MissingSummaryClient())
    assert not (tmp_path / "resume" / "v001").exists()


@pytest.mark.anyio
async def test_agent_authored_package_bypasses_gemini(tmp_path, monkeypatch, synthetic_candidate):
    def fake_compile(_template, _context, output_dir, base_filename, **_kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{base_filename}.pdf").write_bytes(b"synthetic pdf")
        (output_dir / f"{base_filename}.typ").write_text("synthetic typst", encoding="utf-8")
        return {"success": True, "page_count": 1, "text_chars": 200}

    monkeypatch.setattr(engine, "compile_document", fake_compile)
    package = {
        "tailor_strategy": {"target_role_header": "ANALYST", "primary_angle": "Synthetic fit"},
        "resume": {"summary": "Synthetic summary", "experiences": [], "projects": [],
                   "skills": [], "education": [], "certifications": ""},
    }
    job = {"id": "synthetic-job", "company": "Apex Logistics", "title": "Analyst", "raw_text": "Analyze data"}
    result = await engine.tailor_application_documents(job, custom_output_dir=tmp_path,
        gemini_client=ForbiddenClient(), authored_documents=package)
    assert result["success"]
    assert result["manifest"]["tailor_strategy"] == package["tailor_strategy"]
    assert not (tmp_path / "cover-letter").exists()

    letter = await engine.tailor_application_documents(job, document_type="cover_letter",
        custom_output_dir=tmp_path, gemini_client=ForbiddenClient(),
        authored_documents={"cover_letter": {"paragraphs": ["Synthetic letter"]}})
    assert letter["success"]
    assert letter["manifest"]["version"] == "v001"


@pytest.mark.anyio
async def test_new_versions_follow_legacy_versions_without_moving_them(tmp_path, monkeypatch, synthetic_candidate):
    legacy_resume = tmp_path / "versions" / "v001" / "resume"
    legacy_letter = tmp_path / "versions" / "v001" / "cover-letter"
    legacy_resume.mkdir(parents=True)
    legacy_letter.mkdir(parents=True)
    (legacy_resume / "old_resume.pdf").write_bytes(b"legacy resume")
    (legacy_letter / "old_letter.pdf").write_bytes(b"legacy letter")
    (tmp_path / "workspace-metadata.json").write_text(json.dumps({
        "job_id": "synthetic-job", "application_key": "synthetic-job", "version": "v001",
        "resume": {"pdf": str(legacy_resume / "old_resume.pdf")},
        "cover_letter": {"pdf": str(legacy_letter / "old_letter.pdf")},
    }), encoding="utf-8")

    def fake_compile(_template, _context, output_dir, base_filename, **_kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{base_filename}.pdf").write_bytes(b"new pdf")
        (output_dir / f"{base_filename}.typ").write_text("synthetic typst", encoding="utf-8")
        return {"success": True, "page_count": 1, "text_chars": 200}

    monkeypatch.setattr(engine, "compile_document", fake_compile)
    job = {"id": "synthetic-job", "company": "Apex Logistics", "title": "Analyst", "raw_text": "Analyze data"}
    resume = await engine.tailor_application_documents(job, custom_output_dir=tmp_path,
        gemini_client=FakeClient())
    letter = await engine.tailor_application_documents(job, document_type="cover_letter",
        custom_output_dir=tmp_path, gemini_client=FakeClient())

    assert Path(resume["pdf"]).parent == tmp_path / "resume" / "v002"
    assert Path(letter["pdf"]).parent == tmp_path / "cover-letter" / "v002"
    assert [item["version"] for item in scan_document_versions(tmp_path, "resume")["versions"]] == ["v002", "v001"]
    assert [item["version"] for item in scan_document_versions(tmp_path, "cover_letter")["versions"]] == ["v002", "v001"]
    assert (legacy_resume / "old_resume.pdf").read_bytes() == b"legacy resume"
    latest = json.loads((tmp_path / "workspace-metadata.json").read_text(encoding="utf-8"))
    assert "version" not in latest
    assert latest["documents"]["resume"]["version"] == "v002"
    assert latest["documents"]["cover_letter"]["version"] == "v002"


def test_compiler_rejects_multi_page_pdf(tmp_path, monkeypatch):
    def write_two_pages(_source, output):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.add_blank_page(width=612, height=792)
        with open(output, "wb") as stream:
            writer.write(stream)

    monkeypatch.setattr(compiler.typst, "compile", write_two_pages)
    result = compiler.compile_document("cover_letter.typ.j2", {
        "candidate": {"name": "Alex Taylor", "headline": "Analyst", "location": "Remote",
                      "phone": "(555) 019-2834", "email": "alex@example.com",
                      "linkedin": "example.com/profile", "github": "example.com/code",
                      "work_authorization": "Authorized"},
        "letter": {"recipient_title": "Hiring Team", "company_name": "Apex Logistics",
                   "company_location": "Remote", "date": "September 23, 2026",
                   "subject_role": "Analyst", "salutation": "Hiring Team", "paragraphs": ["Hello"]},
    }, tmp_path, "letter")
    assert not result["success"]
    assert result["page_count"] == 2


def test_compiler_rejects_blank_single_page_pdf(tmp_path, monkeypatch):
    def write_blank_page(_source, output):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with open(output, "wb") as stream:
            writer.write(stream)

    monkeypatch.setattr(compiler.typst, "compile", write_blank_page)
    result = compiler.compile_document("cover_letter.typ.j2", {
        "candidate": {"name": "Alex Taylor", "headline": "Analyst", "location": "Remote",
                      "phone": "(555) 019-2834", "email": "alex@example.com",
                      "linkedin": "example.com/profile", "github": "example.com/code",
                      "work_authorization": "Authorized"},
        "letter": {"recipient_title": "Hiring Team", "company_name": "Apex Logistics",
                   "company_location": "Remote", "date": "September 23, 2026",
                   "subject_role": "Analyst", "salutation": "Hiring Team", "paragraphs": ["Hello"]},
    }, tmp_path, "letter")
    assert result["is_single_page"]
    assert not result["success"]


def test_typst_escaping_handles_quotes_and_markup(tmp_path):
    context = {
        "candidate": {"name": "Alex [Taylor]", "headline": "Analyst", "location": "Remote",
                      "phone": "(555) 019-2834", "email": "alex+test@example.com",
                      "linkedin": "example.com/quoted", "github": "example.com/code",
                      "work_authorization": "Authorized"},
        "letter": {"recipient_title": "Hiring Team", "company_name": 'Apex "Data" Logistics',
                   "company_location": "Remote", "date": "September 23, 2026",
                   "subject_role": "Analyst", "salutation": "Hiring Team",
                   "paragraphs": [r"Improved *verified* reporting for #ops at $0 added cost; see [notes]."]},
    }
    result = compiler.compile_document("cover_letter.typ.j2", context, tmp_path, "letter")
    assert result["success"], result.get("error")
    assert result["text_chars"] > 100


def test_application_directory_reused_across_days_and_isolated_by_job(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "APPLICATIONS_DIR", tmp_path)
    first_job = {"id": "job-one", "company": "Apex Logistics", "title": "Analyst"}
    second_job = {"id": "job-two", "company": "Apex Logistics", "title": "Analyst"}
    first_dir = engine._application_dir(first_job, "Apex Logistics", "Analyst", "2026-09-23")
    first_dir.mkdir()
    (first_dir / "workspace-metadata.json").write_text(
        json.dumps({"job_id": "job-one", "application_key": "job-one"}), encoding="utf-8")

    assert engine._application_dir(first_job, "Apex Logistics", "Analyst", "2026-09-24") == first_dir
    assert engine._application_dir(second_job, "Apex Logistics", "Analyst", "2026-09-23") != first_dir


def test_resume_omits_empty_optional_sections(tmp_path):
    context = {
        "candidate": {"name": "Alex Taylor", "location": "Remote", "phone": "(555) 019-2834",
                      "email": "alex@example.com", "linkedin": "example.com/profile",
                      "github": "example.com/code", "work_authorization": "Authorized"},
        "resume": {"target_role": "ANALYST", "summary": "Analyst with experience checking operational records, "
                   "documenting discrepancies, and preparing clear reports for team decisions.",
                   "experiences": [{"company": "Apex Logistics", "dates": "2024-2025",
                                    "title": "Analyst", "location": "Remote",
                                    "bullets": ["Checked source records and documented exceptions for review."]}],
                   "skills": [], "projects": [], "education": [], "certifications": ""},
    }
    result = compiler.compile_document("resume.typ.j2", context, tmp_path, "resume")
    assert result["success"], result.get("error")
    text = PdfReader(result["pdf_path"]).pages[0].extract_text()
    assert "EXPERIENCE" in text
    assert "PROJECTS" not in text
    assert "CERTIFICATIONS" not in text
