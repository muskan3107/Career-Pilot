"""Essential tests. They need no API key and no internet."""
from datetime import date
from pathlib import Path

import pymupdf
import pytest

from careerpilot import agent, llm, tools
from careerpilot.report import build_guide_docx

SAMPLES = Path(__file__).resolve().parents[1] / "sample_data"
JD = (SAMPLES / "sample_job_description.txt").read_text(encoding="utf-8")


def make_pdf(text):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((60, 80), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


# 1. Resume PDF text extraction
def test_extract_resume_text_from_pdf():
    text = tools.extract_resume_text(make_pdf("Skills: Python, SQL and Git for backend projects"))
    assert "Python" in text and "SQL" in text


def test_extract_resume_text_rejects_invalid_pdf():
    with pytest.raises(ValueError):
        tools.extract_resume_text(b"this is not a pdf")
    with pytest.raises(ValueError):
        tools.extract_resume_text(b"")


# 2. Skill matching with known inputs
def test_skill_matching_known_inputs():
    resume_skills = tools.extract_resume_skills("I know Python, SQL and Git. Built projects in JavaScript.")
    assert {"Python", "SQL", "Git", "JavaScript"} <= set(resume_skills)
    assert "Java" not in resume_skills  # 'Java' must not match inside 'JavaScript'
    job = tools.analyze_job_description("Backend engineer needed. Python Python Docker Kubernetes SQL experience.")
    assert job["skills"][0] == "Python"  # mentioned most often
    result = tools.compare_skills(resume_skills, job["skills"])
    assert set(result["matched"]) == {"Python", "SQL"}
    assert set(result["missing"]) == {"Docker", "Kubernetes"}


# 3. Empty / invalid job description
@pytest.mark.parametrize("bad", ["", "   ", None, "too short", "Looking for a friendly person to bake bread and sing."])
def test_invalid_job_description_raises(bad):
    with pytest.raises(ValueError):
        tools.analyze_job_description(bad)


def test_agent_reports_empty_job_description_without_crashing():
    result = agent.run_agent(make_pdf("Python and SQL developer with Git experience"), "", demo=True)
    assert result.guide is None and result.error
    assert result.log[0]["status"] == "failed"


# 4. Missing publication dates / unavailable research
def test_missing_dates_are_labeled_not_invented():
    fake = lambda q, n: [{"title": "Some Guide", "href": "https://example.org/guide"}]
    out = tools.search_resources(["Docker"], search_fn=fake, today=date(2026, 10, 17))
    assert len(out.resources) == 1
    r = out.resources[0]
    assert r.published is None and "not verified" in r.date_note.lower()


def test_old_verified_dates_are_filtered_out():
    fake = lambda q, n: [
        {"title": "Old", "href": "https://example.org/old", "date": "2015-01-01"},
        {"title": "New", "href": "https://example.org/new", "date": "2025-06-01"},
    ]
    out = tools.search_resources(["Docker"], search_fn=fake, today=date(2026, 10, 17))
    assert [r.title for r in out.resources] == ["New"]


def test_unavailable_research_returns_warning_and_no_fake_results():
    def broken(q, n):
        raise ConnectionError("offline")

    out = tools.search_resources(["Docker", "SQL"], search_fn=broken)
    assert out.resources == [] and not out.live
    assert any("unavailable" in w.lower() for w in out.warnings)


# 5. Report generation
def test_report_generation_creates_valid_docx(tmp_path):
    resume = (SAMPLES / "sample_resume.pdf").read_bytes()
    result = agent.run_agent(resume, JD, demo=True)
    data = build_guide_docx(result.guide)
    assert data[:2] == b"PK"  # docx files are zip archives
    path = tmp_path / "guide.docx"
    path.write_bytes(data)
    from docx import Document

    text = "\n".join(p.text for p in Document(str(path)).paragraphs)
    assert "Interview Preparation Guide" in text and "DEMO MODE" in text
    assert "Limitations and uncertainty notes" in text


def test_report_generation_rejects_empty_guide():
    with pytest.raises(ValueError):
        build_guide_docx(None)


# 6. Missing API key / failed API request
def test_missing_api_key_is_handled(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("careerpilot.llm.get_api_key", lambda: None)
    with pytest.raises(llm.LLMError):
        llm.synthesize_with_gemini({"job_title": "x", "job_text": "x", "matched": [], "missing": [],
                                    "candidates": [], "resources": []})
    resume = (SAMPLES / "sample_resume.pdf").read_bytes()
    no_search = lambda q, n: []
    result = agent.run_agent(resume, JD, demo=False, search_fn=no_search)
    assert result.guide is not None  # still produces a basic guide
    llm_step = [s for s in result.log if s["kind"] == "LLM"][0]
    assert llm_step["status"] == "failed"
    assert result.guide["llm_used"] is False


def test_failed_api_request_is_handled(monkeypatch):
    monkeypatch.setattr("careerpilot.llm.get_api_key", lambda: "fake-key")

    def boom(prompt, key, model):
        raise RuntimeError("503 service unavailable")

    monkeypatch.setattr("careerpilot.llm._call_gemini", boom)
    with pytest.raises(llm.LLMError):
        llm.synthesize_with_gemini({"job_title": "x", "job_text": "x", "matched": [], "missing": [],
                                    "candidates": [], "resources": []})


def test_llm_cannot_inject_links_or_unknown_topics():
    resume = (SAMPLES / "sample_resume.pdf").read_bytes()

    def sneaky_llm(ctx):
        return {"target_job_summary": "See https://evil.example/x for more",
                "prioritized_topics": [{"topic": "Made-Up Topic", "reason": "x", "resource_ids": [99]},
                                       {"topic": ctx["candidates"][0], "reason": "ok https://evil.example", "resource_ids": [99]}],
                "preparation_strategy": ["go to https://evil.example"], "practice_questions": []}

    result = agent.run_agent(resume, JD, demo=False, llm_fn=sneaky_llm, search_fn=lambda q, n: [])
    g = result.guide
    blob = str(g)
    assert "evil.example" not in blob
    assert "Made-Up Topic" not in [t["topic"] for t in g["topics"]]
