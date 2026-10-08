import asyncio
import importlib

import httpx
import pytest
from fastapi import HTTPException

import_job = importlib.import_module("app.api.import_job")
DESCRIPTION = "Operations Analyst supporting SQL reporting, data validation, and stakeholder performance reviews."
HOST = "https://sample.wd3.myworkdayjobs.com"
JOB_PATH = "/job/Example-City/Operations-Analyst_R123"


@pytest.mark.parametrize("prefix", ["/Careers", "/en-US/Careers", "/zh-TW/Careers"])
def test_workday_fetch_reads_dynamic_posting(monkeypatch, prefix):
    calls = []

    async def fetch(url, headers=None):
        calls.append(url)
        if "/wday/cxs/" in url:
            return httpx.Response(200, json={"jobPostingInfo": {
                "jobDescription": f"<p>{DESCRIPTION}</p>",
            }}, request=httpx.Request("GET", url))
        return httpx.Response(200, json={"widget": "redirect", "externalSpa": True},
                              request=httpx.Request("GET", url))

    monkeypatch.setattr(import_job, "_fetch_public_page", fetch)
    result = asyncio.run(import_job.fetch_url_page(HOST + prefix + JOB_PATH + "?source=alert"))
    assert result.text == DESCRIPTION
    assert result.extraction_method == "Workday job posting"
    assert calls == [HOST + "/wday/cxs/sample/Careers" + JOB_PATH]


@pytest.mark.parametrize("payload", [{}, {"jobPostingInfo": []},
                                      {"jobPostingInfo": {"jobDescription": "too short"}}])
def test_workday_shell_is_not_returned_as_jd(monkeypatch, payload):
    async def fetch(url, headers=None):
        if "/wday/cxs/" in url:
            return httpx.Response(200, json=payload, request=httpx.Request("GET", url))
        return httpx.Response(200, json={"widget": "redirect", "url": JOB_PATH, "externalSpa": True},
                              request=httpx.Request("GET", url))

    monkeypatch.setattr(import_job, "_fetch_public_page", fetch)
    with pytest.raises(HTTPException, match="job description"):
        asyncio.run(import_job.fetch_url_page(HOST + "/Careers" + JOB_PATH))


def test_workday_api_failure_falls_back_to_html(monkeypatch):
    async def fetch(url, headers=None):
        if "/wday/cxs/" in url:
            return httpx.Response(404, request=httpx.Request("GET", url))
        return httpx.Response(200, text=f'<div data-automation-id="jobPostingDescription">{DESCRIPTION}</div>',
                              request=httpx.Request("GET", url))

    monkeypatch.setattr(import_job, "_fetch_public_page", fetch)
    result = asyncio.run(import_job.fetch_url_page(HOST + "/Careers" + JOB_PATH))
    assert result.text == DESCRIPTION
    assert result.extraction_method == "Workday job description"


def test_workday_api_keeps_response_size_guard(monkeypatch):
    async def fetch(url, headers=None):
        raise HTTPException(status_code=400, detail="The job page exceeded the response size limit")

    monkeypatch.setattr(import_job, "_fetch_public_page", fetch)
    with pytest.raises(HTTPException, match="size limit"):
        asyncio.run(import_job.fetch_url_page(HOST + "/Careers" + JOB_PATH))


@pytest.mark.parametrize("url", [
    "https://sample.wd3.myworkdayjobs.com.attacker.example/Careers" + JOB_PATH,
    HOST + "/Careers",
    HOST + "/Careers/job/%2e%2e/role",
    HOST + "/Careers/job/%2Fadmin/role",
])
def test_workday_endpoint_rejects_non_postings_and_unsafe_paths(url):
    assert import_job._workday_job_endpoint(url) is None


def test_workday_encoded_location_is_preserved():
    endpoint = import_job._workday_job_endpoint(HOST + "/en-US/Careers/job/Example%20City/Role_R123")
    assert endpoint == HOST + "/wday/cxs/sample/Careers/job/Example%20City/Role_R123"
