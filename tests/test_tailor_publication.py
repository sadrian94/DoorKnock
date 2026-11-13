import json
import hashlib
import threading
import sys
from concurrent.futures import ThreadPoolExecutor
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
        alignment = [{"keyword": "data", "requirement": "Analyze data", "support": "unsupported",
                      "evidence_ids": [], "placements": [], "boundary": "No work evidence in this fixture."}]
        if "Review the completed document" in prompt:
            return {"claim_review": {"status": "ready", "findings": []}}
        if "Write only the resume Experience and Projects" in prompt:
            return {"experiences": [], "projects": []}
        if "Write only resume Skills, Education" in prompt:
            return {"skills": [], "education": [], "certifications": ""}
        if "Write only the resume Summary" in prompt:
            return {"summary": "Synthetic summary"}
        if "cover letter" in prompt.lower():
            return {"paragraphs": ["Synthetic letter"]}
        if 'Allowed placements: paragraphs' in prompt:
            return {"keyword_alignment": alignment}
        return {"target_role_header": "ANALYST", "primary_angle": "Synthetic fit", "keyword_alignment": alignment}


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
@pytest.mark.parametrize("single_page_preference", [True, False])
@pytest.mark.parametrize("authored", [True, False])
async def test_first_resume_allows_multiple_pages_then_follows_preference(
    tmp_path, monkeypatch, synthetic_candidate, single_page_preference, authored,
):
    monkeypatch.setattr(engine, "get_resume_settings", lambda: {
        "require_single_page": single_page_preference,
    })
    summary = "Checked operational records and documented discrepancies for team review. " * 160

    class LongResumeClient(FakeClient):
        async def generate_json(self, **kwargs):
            if "Write only the resume Summary" in kwargs["prompt"]:
                self.prompts.append(kwargs["prompt"])
                return {"summary": summary}
            return await super().generate_json(**kwargs)

    package = {
        "tailor_strategy": {"target_role_header": "ANALYST", "primary_angle": "Synthetic fit"},
        "resume": {"summary": summary, "experiences": [], "projects": [],
                   "skills": [], "education": [], "certifications": ""},
    }
    job = {"id": "synthetic-job", "company": "Apex Logistics", "title": "Analyst", "raw_text": "Analyze data"}
    # A cover letter has its own version series and must still reject multiple pages.
    rejected_letter = await engine.tailor_application_documents(
        job, document_type="cover_letter", custom_output_dir=tmp_path,
        authored_documents={"cover_letter": {"paragraphs": [summary]}},
    )
    assert not rejected_letter["success"]
    assert rejected_letter["compilation"]["page_limit_required"]
    assert not (tmp_path / "cover-letter" / "v001").exists()
    letter = await engine.tailor_application_documents(
        job, document_type="cover_letter", custom_output_dir=tmp_path,
        authored_documents={"cover_letter": {"paragraphs": ["Checked operational records for review."]}},
    )
    assert letter["success"]

    client = LongResumeClient()
    arguments = {"authored_documents": package} if authored else {"gemini_client": client}
    first = await engine.tailor_application_documents(job, custom_output_dir=tmp_path, **arguments)
    assert first["success"], first.get("compilation")
    assert first["manifest"]["version"] == "v001"
    assert first["manifest"]["page_count"] > 1
    assert not first["manifest"]["page_limit_required"]
    first_pdf = Path(first["pdf"]).read_bytes()
    reader = PdfReader(first["pdf"])
    assert len(reader.pages) > 1
    assert "SUMMARY" in reader.pages[0].extract_text()
    if not authored:
        assert "two pages are acceptable" in client.prompts[1]

    second = await engine.tailor_application_documents(job, custom_output_dir=tmp_path, **arguments)
    if single_page_preference:
        assert not second["success"]
        assert second["compilation"]["page_limit_required"]
        assert second["compilation"]["page_count"] > 1
        assert not (tmp_path / "resume" / "v002").exists()
        latest = json.loads((tmp_path / "workspace-metadata.json").read_text(encoding="utf-8"))
        assert latest["documents"]["resume"]["version"] == "v001"
    else:
        assert second["success"]
        assert second["manifest"]["version"] == "v002"
        assert not second["manifest"]["page_limit_required"]
    assert Path(first["pdf"]).read_bytes() == first_pdf


@pytest.mark.anyio
async def test_retailor_publishes_distinct_versions(tmp_path, monkeypatch, synthetic_candidate):
    def fake_compile(_template, _context, output_dir, base_filename, **_kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf = output_dir / f"{base_filename}.pdf"
        typ = output_dir / f"{base_filename}.typ"
        pdf.write_bytes(b"synthetic pdf")
        typ.write_text("synthetic typst", encoding="utf-8")
        return {"success": True, "is_single_page": True, "page_count": 1,
                "pdf_path": str(pdf), "typ_path": str(typ)}

    monkeypatch.setattr(engine, "compile_document", fake_compile)
    job = {"id": "synthetic-job", "company": "Apex Logistics", "title": "Analyst", "raw_text": "Analyze data"}
    client = FakeClient()
    first = await engine.tailor_application_documents(job, custom_output_dir=tmp_path, gemini_client=client)
    second = await engine.tailor_application_documents(job, custom_output_dir=tmp_path, gemini_client=FakeClient())
    letter_client = FakeClient()
    letter = await engine.tailor_application_documents(job, document_type="cover_letter",
        custom_output_dir=tmp_path, gemini_client=letter_client)

    assert first["success"] and second["success"] and letter["success"]
    assert len(client.prompts) == 5
    assert len(letter_client.prompts) == 3
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
    assert "ADDITIONAL EXPERIENCE" not in text
    assert "PROJECTS" not in text
    assert "CERTIFICATIONS" not in text


@pytest.mark.anyio
@pytest.mark.parametrize("document_type", ["resume", "cover_letter"])
async def test_reviewed_preview_publishes_exact_bytes_without_new_compile(tmp_path, monkeypatch, synthetic_candidate, document_type):
    monkeypatch.setattr(engine, "get_resume_settings", lambda: {"require_single_page": True})
    job = {"id": "synthetic-preview", "company": "Example Co", "title": "Analyst", "raw_text": "Analyze data"}
    package = ({"tailor_strategy": {"target_role_header": "ANALYST", "primary_angle": "Synthetic fit"},
                "resume": {"summary": "Analyzed operational records and prepared reports for team review. " * 3,
                           "experiences": [], "projects": [], "skills": [], "education": [], "certifications": ""}}
               if document_type == "resume" else
               {"cover_letter": {"paragraphs": ["Analyzed operational records and prepared reports for team review. " * 3]}})
    result = await engine.tailor_application_documents(job, document_type=document_type,
        custom_output_dir=tmp_path, authored_documents=package, preview_only=True)
    assert result["success"]
    preview = Path(result["preview_dir"])
    assert Path(result["compilation"]["pdf_path"]).is_file()
    assert Path(result["compilation"]["typ_path"]).is_file()
    original_pdf = Path(result["pdf"]).read_bytes()
    assert not (tmp_path / "workspace-metadata.json").exists()
    assert not (tmp_path / "resume").exists() and not (tmp_path / "cover-letter").exists()
    with pytest.raises(ValueError, match="hash does not match"):
        engine.publish_reviewed_preview(preview, "0" * 64)
    sidecar = preview / "keyword-review.json"
    original_sidecar = sidecar.read_bytes()
    sidecar.write_bytes(b"altered")
    with pytest.raises(ValueError, match="artifact changed"):
        engine.publish_reviewed_preview(preview, result["pdf_sha256"])
    sidecar.write_bytes(original_sidecar)
    pdf_path = Path(result["pdf"])
    pdf_path.write_bytes(b"modified preview")
    with pytest.raises(ValueError, match="artifact changed"):
        engine.publish_reviewed_preview(preview, result["pdf_sha256"])
    pdf_path.write_bytes(original_pdf)
    monkeypatch.setattr(engine, "compile_document", lambda *a, **kw: pytest.fail("must not recompile"))
    published = engine.publish_reviewed_preview(preview, result["pdf_sha256"])
    assert Path(published["pdf"]).read_bytes() == original_pdf
    assert published["manifest"]["version"] == "v001"
    assert published["manifest"]["reviewed_pdf_sha256"] == result["pdf_sha256"]
    latest = json.loads((tmp_path / "workspace-metadata.json").read_text(encoding="utf-8"))
    assert latest["documents"][document_type]["version"] == "v001"
    assert not preview.exists()
    resolved = scan_document_versions(tmp_path, document_type)["versions"][0]
    assert Path(resolved["file_path"]).read_bytes() == original_pdf


@pytest.fixture
def make_preview(tmp_path, synthetic_candidate, monkeypatch):
    monkeypatch.setattr(engine, "get_resume_settings", lambda: {"require_single_page": True})

    async def create(document_type="resume", repeats=3, output_dir=None):
        text = "Analyzed operational records and prepared reports for team review. " * repeats
        package = ({"tailor_strategy": {"target_role_header": "ANALYST"},
                    "resume": {"summary": text, "experiences": [], "projects": [],
                               "skills": [], "education": [], "certifications": ""}}
                   if document_type == "resume" else {"cover_letter": {"paragraphs": [text]}})
        result = await engine.tailor_application_documents(
            {"id": "synthetic-preview", "company": "Example Co", "title": "Analyst", "raw_text": "Analyze data"},
            document_type=document_type, custom_output_dir=output_dir or tmp_path, authored_documents=package, preview_only=True)
        assert result["success"]
        return Path(result["preview_dir"]), result["pdf_sha256"]
    return create


@pytest.mark.anyio
@pytest.mark.parametrize("changed_field", ["sidecar", "page_count", "document_type", "job_id", "application_key"])
async def test_preview_rejects_extra_files_and_rewritten_metadata(make_preview, tmp_path, changed_field):
    preview, digest = await make_preview()
    extra = preview / "final.pdf"
    extra.write_bytes(b"unreviewed replacement")
    with pytest.raises(ValueError, match="Unexpected"):
        engine.publish_reviewed_preview(preview, digest)
    extra.unlink()
    metadata_path = preview / "preview.json"
    original = metadata_path.read_bytes()
    metadata = json.loads(original)
    sidecar = preview / "keyword-review.json"
    original_sidecar = sidecar.read_bytes()
    if changed_field == "sidecar":
        sidecar.write_bytes(b"rewritten")
        metadata["hashes"][sidecar.name] = hashlib.sha256(sidecar.read_bytes()).hexdigest()
    else:
        metadata[changed_field] = {"page_count": 999, "document_type": "cover_letter",
                                   "job_id": "other-job", "application_key": "other-job"}[changed_field]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata changed"):
        engine.publish_reviewed_preview(preview, digest)
    assert not scan_document_versions(tmp_path, "resume")["available"]
    metadata_path.write_bytes(original)
    sidecar.write_bytes(original_sidecar)
    assert engine.publish_reviewed_preview(preview, digest)["success"]


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["version_manifest", "index_write", "move", "index_replace"])
async def test_preview_publication_failure_is_retryable(make_preview, tmp_path, monkeypatch, failure):
    preview, digest = await make_preview()
    initial = engine.publish_reviewed_preview(preview, digest)
    previous_index = (tmp_path / "workspace-metadata.json").read_bytes()
    preview, digest = await make_preview()
    write_text, rename, replace = Path.write_text, Path.rename, Path.replace

    def fail_write(path, *args, **kwargs):
        if ((failure == "version_manifest" and path == preview / "workspace-metadata.json") or
                (failure == "index_write" and path.name.startswith(".workspace-metadata-"))):
            raise OSError("injected failure")
        return write_text(path, *args, **kwargs)

    def fail_rename(path, target):
        if failure == "move" and path == preview:
            raise OSError("injected failure")
        return rename(path, target)

    def fail_replace(path, target):
        if failure == "index_replace" and Path(target) == tmp_path / "workspace-metadata.json":
            raise OSError("injected failure")
        return replace(path, target)

    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "write_text", fail_write)
        patcher.setattr(Path, "rename", fail_rename)
        patcher.setattr(Path, "replace", fail_replace)
        with pytest.raises(OSError, match="injected"):
            engine.publish_reviewed_preview(preview, digest)
    assert preview.is_dir()
    assert not (preview / "workspace-metadata.json").exists()
    assert (tmp_path / "workspace-metadata.json").read_bytes() == previous_index
    assert not (tmp_path / "resume" / "v002").exists()
    assert not list(tmp_path.glob(".workspace-metadata-*.json"))
    assert not (tmp_path / ".tailor-publication.lock").exists()
    published = engine.publish_reviewed_preview(preview, digest)
    assert published["manifest"]["version"] == "v002"
    assert Path(initial["pdf"]).is_file()


@pytest.mark.anyio
async def test_publish_uses_current_version_and_page_policy(make_preview, tmp_path):
    long_preview, long_digest = await make_preview(repeats=160)
    short_preview, short_digest = await make_preview()
    other_preview, other_digest = await make_preview()
    assert engine.publish_reviewed_preview(short_preview, short_digest)["manifest"]["version"] == "v001"
    with pytest.raises(ValueError, match="page limit"):
        engine.publish_reviewed_preview(long_preview, long_digest)
    assert long_preview.exists()
    published = engine.publish_reviewed_preview(other_preview, other_digest)
    assert published["manifest"]["version"] == "v002"
    assert published["manifest"]["page_limit_required"] is True
    assert len(PdfReader(published["pdf"]).pages) == published["manifest"]["page_count"] == 1


@pytest.mark.anyio
async def test_shared_lock_blocks_overlapping_publishers(make_preview, tmp_path, monkeypatch, synthetic_candidate):
    preview, digest = await make_preview()
    letter, letter_digest = await make_preview("cover_letter")
    entered, release = threading.Event(), threading.Event()
    original = engine._publish_bundle

    def paused(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original(*args, **kwargs)

    monkeypatch.setattr(engine, "_publish_bundle", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        publishing = pool.submit(engine.publish_reviewed_preview, preview, digest)
        try:
            assert entered.wait(10)
            with pytest.raises(ValueError, match="Another publication"):
                engine.publish_reviewed_preview(letter, letter_digest)
            with pytest.raises(ValueError, match="Another publication"):
                await engine.tailor_application_documents(
                    {"id": "synthetic-preview", "company": "Example Co", "title": "Analyst"},
                    custom_output_dir=tmp_path, authored_documents={
                        "tailor_strategy": {}, "resume": {"summary": "Synthetic summary for team review. " * 5,
                        "experiences": [], "projects": [], "skills": [], "education": [], "certifications": ""}})
        finally:
            release.set()
        assert publishing.result()["success"]
    monkeypatch.setattr(engine, "_publish_bundle", original)
    assert engine.publish_reviewed_preview(letter, letter_digest)["success"]
    latest = json.loads((tmp_path / "workspace-metadata.json").read_text(encoding="utf-8"))
    assert set(latest["documents"]) == {"resume", "cover_letter"}


@pytest.mark.anyio
async def test_preview_relocation_and_invalid_index_fail_closed(make_preview, tmp_path):
    preview, digest = await make_preview()
    other_app = tmp_path / "other-application"
    other_app.mkdir()
    receipt = preview.with_suffix(".sha256")
    moved = preview.rename(other_app / preview.name)
    moved_receipt = receipt.rename(other_app / receipt.name)
    with pytest.raises(ValueError, match="metadata changed"):
        engine.publish_reviewed_preview(moved, digest)
    moved.rename(preview)
    moved_receipt.rename(receipt)
    index = tmp_path / "workspace-metadata.json"
    for invalid in ["{invalid", "[]", '{"application_key":"other-job"}']:
        index.write_text(invalid, encoding="utf-8")
        with pytest.raises(ValueError):
            engine.publish_reviewed_preview(preview, digest)
        assert preview.exists() and index.read_text(encoding="utf-8") == invalid
        assert not (tmp_path / "resume" / "v001").exists()
    index.unlink()
    assert engine.publish_reviewed_preview(preview, digest)["success"]


@pytest.mark.anyio
@pytest.mark.parametrize("document_type", ["resume", "cover_letter"])
async def test_cli_preview_publish_round_trip(tmp_path, monkeypatch, synthetic_candidate, capsys, document_type):
    from app.tailor import cli
    monkeypatch.setattr(engine, "APPLICATIONS_DIR", tmp_path)
    monkeypatch.setattr(cli, "APPLICATIONS_DIR", tmp_path)
    monkeypatch.setattr(engine, "get_ai_client", lambda: pytest.fail("CLI must not call provider"))
    jd = tmp_path / "jd.txt"
    jd.write_text("Analyze data", encoding="utf-8")
    text = "Analyzed operational records and prepared reports for team review. " * 3
    package = {"tailor_strategy": {}, "resume": {"summary": text, "experiences": [], "projects": [],
               "skills": [], "education": [], "certifications": ""}, "cover_letter": {"paragraphs": [text]}}
    authored = tmp_path / "authored.json"
    authored.write_text(json.dumps(package), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["tailor", "--jd-file", str(jd), "--company", "Example Co",
        "--title", "Analyst", "--document-type", document_type, "--authored-json", str(authored), "--preview-only"])
    await cli.run_cli()
    output = capsys.readouterr().out
    result = json.loads(output[output.index("{"):])
    preview = Path(result["preview_dir"])
    original_pdf = Path(result["pdf"]).read_bytes()
    assert not (preview.parent / "workspace-metadata.json").exists()
    monkeypatch.setattr(engine, "compile_document", lambda *a, **kw: pytest.fail("publish must not compile"))
    monkeypatch.setattr(sys, "argv", ["tailor", "--publish-preview", str(preview),
                                    "--reviewed-pdf-sha256", result["pdf_sha256"]])
    await cli.run_cli()
    published = json.loads(capsys.readouterr().out)
    assert Path(published["pdf"]).read_bytes() == original_pdf
    index = json.loads((preview.parent / "workspace-metadata.json").read_text(encoding="utf-8"))
    assert index["documents"][document_type]["version"] == "v001"
    assert Path(index["documents"][document_type]["manifest"]).is_file()


@pytest.mark.anyio
async def test_unpublished_application_reused_across_days(tmp_path, monkeypatch, synthetic_candidate):
    from datetime import date
    from app import documents
    monkeypatch.setattr(engine, "APPLICATIONS_DIR", tmp_path)
    monkeypatch.setattr(documents, "APPLICATIONS_DIR", tmp_path)
    monkeypatch.setattr(documents, "WORKSPACE_DIR", tmp_path)
    job = {"id": "synthetic-cross-day", "company": "Example Co", "title": "Analyst", "raw_text": "Analyze data"}
    monkeypatch.setattr(documents.crud, "get_job_by_id", lambda _id: job)
    text = "Analyzed operational records and prepared reports for team review. " * 3
    package = {"tailor_strategy": {}, "resume": {"summary": text, "experiences": [], "projects": [],
               "skills": [], "education": [], "certifications": ""}, "cover_letter": {"paragraphs": [text]}}
    # Identity is stable even when no preview or index has been written yet.
    assert engine._application_dir(job, "Example Co", "Analyst", "2026-11-12") == engine._application_dir(
        job, "Renamed Company", "Changed Title", "2026-11-13")
    monkeypatch.setattr(engine, "local_today", lambda: date(2026, 11, 12))
    resume = await engine.tailor_application_documents(job, authored_documents=package, preview_only=True)
    monkeypatch.setattr(engine, "local_today", lambda: date(2026, 11, 13))
    letter = await engine.tailor_application_documents(job, document_type="cover_letter",
                                                     authored_documents=package, preview_only=True)
    app_dir = Path(resume["preview_dir"]).parent
    assert Path(letter["preview_dir"]).parent == app_dir
    assert not (app_dir / "workspace-metadata.json").exists()
    for result in (letter, resume):
        assert engine.publish_reviewed_preview(Path(result["preview_dir"]), result["pdf_sha256"])["success"]
    assert documents.find_application_directory(job["id"]) == app_dir
    for doc_type in ("resume", "cover_letter"):
        path = documents.resolve_document_file_path(job["id"], doc_type)
        assert path is not None and path.is_file()
    assert len(list(tmp_path.glob("*/workspace-metadata.json"))) == 1


@pytest.mark.anyio
@pytest.mark.parametrize("prior_version", [False, True])
@pytest.mark.parametrize("via_preview", [False, True])
async def test_resolver_hides_uncommitted_publication(make_preview, tmp_path, monkeypatch, prior_version, via_preview):
    if prior_version:
        preview, digest = await make_preview()
        engine.publish_reviewed_preview(preview, digest)
    previous = scan_document_versions(tmp_path, "resume")
    replace = Path.replace
    observations = []

    def fail_commit(path, target):
        if Path(target) == tmp_path / "workspace-metadata.json":
            observations.append(scan_document_versions(tmp_path, "resume"))
            raise OSError("injected before commit")
        return replace(path, target)

    preview, digest = await make_preview()
    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "replace", fail_commit)
        with pytest.raises(OSError, match="before commit"):
            if via_preview:
                engine.publish_reviewed_preview(preview, digest)
            else:
                await engine.tailor_application_documents(
                    {"id": "synthetic-preview", "company": "Example Co", "title": "Analyst"},
                    custom_output_dir=tmp_path, authored_documents={"tailor_strategy": {}, "resume": {
                        "summary": "Analyzed operational records and prepared reports for team review. " * 3,
                        "experiences": [], "projects": [], "skills": [], "education": [], "certifications": ""}})
    assert len(observations) == 1
    assert observations[0] == previous == scan_document_versions(tmp_path, "resume")
    assert preview.exists()
    published = engine.publish_reviewed_preview(preview, digest)
    resolved = scan_document_versions(tmp_path, "resume")
    assert resolved["latest_version"] == published["manifest"]["version"]
    assert len(resolved["versions"]) == (2 if prior_version else 1)


@pytest.mark.anyio
async def test_existing_dated_preview_reused_and_split_publication_rejected(make_preview, tmp_path, monkeypatch):
    # Emulate a valid preview created in an older date-named application directory.
    app_dir = tmp_path / "2026-11-12-example-analyst"
    preview, digest = await make_preview(output_dir=app_dir)
    monkeypatch.setattr(engine, "APPLICATIONS_DIR", tmp_path)
    job = {"id": "synthetic-preview"}
    assert engine._application_dir(job, "Example Co", "Analyst", "2026-11-13") == app_dir
    other_app = tmp_path / "2026-11-13-duplicate"
    other_app.mkdir()
    (other_app / "workspace-metadata.json").write_text(
        json.dumps({"application_key": "synthetic-preview"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Multiple application"):
        engine.publish_reviewed_preview(preview, digest)
    assert preview.exists() and not scan_document_versions(app_dir, "resume")["available"]
    (other_app / "workspace-metadata.json").unlink()
    assert engine.publish_reviewed_preview(preview, digest)["success"]


@pytest.mark.anyio
async def test_resolver_never_promotes_orphaned_indexed_version(make_preview, tmp_path):
    preview, digest = await make_preview()
    initial = engine.publish_reviewed_preview(preview, digest)
    orphan = tmp_path / "resume" / "v002"
    orphan.mkdir()
    (orphan / "workspace-metadata.json").write_text(json.dumps({"publication_protocol": "indexed-v1"}), encoding="utf-8")
    (orphan / "final.pdf").write_bytes(b"orphan from an interrupted publication")
    assert scan_document_versions(tmp_path, "resume")["latest_version"] == "v001"
    preview, digest = await make_preview()
    published = engine.publish_reviewed_preview(preview, digest)
    assert published["manifest"]["version"] == "v003"
    assert [entry["version"] for entry in scan_document_versions(tmp_path, "resume")["versions"]] == ["v003", "v001"]
    # New-format resolution also ignores later unindexed additions to a bundle.
    (Path(initial["pdf"]).parent / "final.pdf").write_bytes(b"unindexed replacement")
    assert scan_document_versions(tmp_path, "resume")["versions"][1]["file_path"] == initial["pdf"]


def test_missing_text_does_not_retry_all_resume_layouts(tmp_path, monkeypatch):
    calls = []
    def blank_pdf(_source, output):
        calls.append(1)
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with open(output, "wb") as stream:
            writer.write(stream)
    monkeypatch.setattr(compiler.typst, "compile", blank_pdf)
    context = {"candidate": {"name": "Example", "location": "", "phone": "", "email": "",
                              "linkedin": "", "github": "", "work_authorization": ""},
               "resume": {"target_role": "Analyst", "summary": "Example", "experiences": [],
                          "additional_experiences": [], "projects": [], "skills": [], "education": [],
                          "certifications": ""}}
    result = compiler.compile_document("resume.typ.j2", context, tmp_path, "blank", require_single_page=True)
    assert not result["success"] and not result["text_complete"]
    assert len(calls) == 1


@pytest.mark.anyio
async def test_additional_experiences_and_optional_github_suppression(tmp_path, monkeypatch, synthetic_candidate):
    resume_context = {
        "candidate": {"name": "Alex Taylor", "location": "Remote", "phone": "(555) 019-2834",
                      "email": "alex@example.com", "linkedin": "example.com/profile",
                      "github": "", "work_authorization": "Authorized"},
        "resume": {
            "target_role": "OPERATIONS ANALYST",
            "summary": "Operations analyst with reconciliation and documentation experience.",
            "experiences": [{"company": "Apex Logistics", "dates": "2024-2025",
                             "title": "Analyst", "location": "Remote",
                             "bullets": ["Checked source records and documented exceptions for review."]}],
            "additional_experiences": [{"company": "Side Quality Co.", "dates": "2026-Present",
                                        "title": "Reviewer (Contract)", "location": "Remote",
                                        "bullets": ["Audited written records against source documentation."]}],
            "skills": [], "projects": [], "education": [], "certifications": "",
        },
    }
    resume_res = compiler.compile_document("resume.typ.j2", resume_context, tmp_path, "resume")
    assert resume_res["success"], resume_res.get("error")
    resume_text = PdfReader(resume_res["pdf_path"]).pages[0].extract_text()
    assert "ADDITIONAL EXPERIENCE" in resume_text
    assert "Side Quality Co." in resume_text
    assert "example.com/profile" in resume_text
    assert "example.com/profile |" not in resume_text

    monkeypatch.setattr(engine, "get_resume_settings", lambda: {"require_single_page": True})
    job = {"id": "synthetic-job-gh", "company": "Apex Logistics", "title": "Analyst", "raw_text": ""}
    letter_res = await engine.tailor_application_documents(
        job,
        document_type="cover_letter",
        custom_output_dir=tmp_path,
        authored_documents={
            "candidate": {"github": ""},
            "cover_letter": {"paragraphs": ["Checked source records and documented exceptions for review."]},
        },
    )
    assert letter_res["success"], letter_res.get("compilation")
    letter_text = PdfReader(letter_res["pdf"]).pages[0].extract_text()
    assert "example.com/profile" in letter_text
    assert "example.com/code" not in letter_text
    assert "example.com/profile |" not in letter_text
