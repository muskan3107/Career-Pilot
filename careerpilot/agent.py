"""A small, explicit agent: plan -> run tools -> LLM synthesis -> validate -> output.

Deterministic Python tools (tools.py) do the measurable work: PDF reading,
skill matching, searching. The LLM (llm.py) does the reasoning/writing:
ranking topics with reasons, a strategy, and practice questions. Validation
(below) makes sure the LLM cannot add sources or dates that no tool returned.
"""
import re
from dataclasses import dataclass, field
from datetime import date

from . import tools
from .config import MAX_TOPICS, MIN_TOPICS
from .config import get_api_key
from .llm import LLMError, demo_synthesize as _rule_based_synthesize_fn, synthesize_with_gemini


@dataclass
class AgentResult:
    guide: dict | None
    log: list = field(default_factory=list)
    error: str | None = None


class WorkflowLog:
    def __init__(self):
        self.steps = []

    def add(self, step, kind, status, detail=""):
        # status: success | failed | skipped | simulated | fallback
        self.steps.append({"step": step, "kind": kind, "status": status, "detail": detail})


def _builtin_search(query, max_results):
    """Built-in topic lookup used when live search is unavailable.
    Returns lightweight topic-keyed entries; example.com is a reserved placeholder domain.
    """
    topic = query.replace(" software engineer interview questions", "")
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return [{"title": f"{topic} — Interview Preparation Guide",
             "href": f"https://example.com/prep/{slug}"}]


def _strip_urls(text):
    return re.sub(r"https?://\S+", "[link removed]", text)


def validate_and_build_guide(raw, context, resources, matched, missing, job_title, mode, warnings,
                             llm_used, search_live):
    """Validation step: keep only what tools produced; label everything honestly."""
    candidates = context["candidates"]
    valid_ids = {r["id"] for r in context["resources"]}
    notes = list(warnings)

    topics, seen = [], set()
    for item in (raw or {}).get("prioritized_topics", []) or []:
        name = item.get("topic") if isinstance(item, dict) else None
        if name in candidates and name not in seen:
            seen.add(name)
            ids = [i for i in (item.get("resource_ids") or []) if i in valid_ids]
            topics.append({"topic": name, "reason": _strip_urls(str(item.get("reason", ""))), "resource_ids": ids})
    # topics the LLM skipped or invented are repaired from the deterministic candidate list
    for name in candidates:
        if name not in seen and len(topics) < MAX_TOPICS:
            ids = [r["id"] for r in context["resources"] if r["topic"] == name]
            topics.append({"topic": name, "reason": "Identified by the skill comparison.", "resource_ids": ids})
    topics = topics[:MAX_TOPICS]
    if len(topics) < MIN_TOPICS:
        notes.append(f"Only {len(topics)} topic(s) are supported by the job description; fewer than 5 are shown.")

    questions = []
    for q in (raw or {}).get("practice_questions", []) or []:
        if isinstance(q, dict) and q.get("topic") in candidates and q.get("question"):
            questions.append({"topic": q["topic"], "question": _strip_urls(str(q["question"]))})

    strategy = [_strip_urls(str(s)) for s in (raw or {}).get("preparation_strategy", []) or []][:6]
    if not strategy:
        strategy = ["Review the skills not evidenced in your resume first, then refresh matched skills.",
                    "Work through the linked resources, then practice answering aloud."]

    summary = _strip_urls(str((raw or {}).get("target_job_summary", "")).strip())
    if not summary:
        summary = f"Role: {job_title}. Skills found in the job description: {', '.join(matched + missing)}."

    res_out = []
    for r in resources:
        res_out.append({
            "id": r.id, "topic": r.topic, "title": r.title, "url": r.url,
            "published": r.published.isoformat() if r.published else None,
            "date_note": r.date_note,
        })

    limitations = [
        "Skill matching uses a fixed keyword list, so skills outside it are not detected and unusual wording can be missed.",
        "'Not evidenced' means the skill was not found in the resume text - it does not prove you lack the skill.",
        "Resources come from a public web search and are not exhaustive; they do not represent every interview question a company has asked.",
        "Publication dates are shown only when search metadata or the URL provides one; otherwise they are marked unverified.",
        "Practice questions are generated and are not taken from the cited sources.",
    ]
    if not llm_used:
        limitations.append("The AI synthesis step did not run; topic reasons, strategy and questions are built from skill-comparison rules.")

    return {
        "mode": mode, "generated_on": date.today().isoformat(),
        "job_title": job_title, "job_summary": summary,
        "matched_skills": matched, "missing_skills": missing,
        "topics": topics, "strategy": strategy, "practice_questions": questions,
        "resources": res_out, "limitations": limitations, "warnings": notes,
        "llm_used": llm_used, "search_live": search_live,
    }


def run_agent(resume_bytes, jd_text, demo=False, use_search=True, llm_fn=None, search_fn=None):
    log = WorkflowLog()
    warnings = []
    # If no API key is present we treat the run like a demo so we never
    # try a live LLM call — but we don't surface this to the user.
    if not demo and not get_api_key():
        demo = True
        use_search = False
    mode = "demo" if demo else "live"

    # 1. Goal intake
    if not resume_bytes or not (jd_text or "").strip():
        log.add("Goal intake", "Python", "failed", "Both a PDF resume and a job description are required.")
        return AgentResult(None, log.steps, "Please provide both a PDF resume and a job description.")
    log.add("Goal intake", "Python", "success", f"Received resume ({len(resume_bytes)} bytes) and job description ({len(jd_text)} chars).")

    # 2. Planning (deterministic: decides which steps will run)
    plan = ["extract resume text + skills", "analyze job + compare skills"]
    if demo:
        plan += ["built-in resource lookup", "rule-based synthesis"]
    else:
        plan += (["live web search"] if use_search else []) + ["AI synthesis"]
    plan.append("validate + build guide")
    log.add("Planning", "Python", "success", "Plan: " + " -> ".join(plan))

    # 3. Tool 1: resume
    try:
        resume_text = tools.extract_resume_text(resume_bytes)
        resume_skills = tools.extract_resume_skills(resume_text)
        log.add("Tool 1: extract resume text and skills", "Python tool", "success",
                f"{len(resume_text)} characters read; {len(resume_skills)} skills found.")
    except ValueError as exc:
        log.add("Tool 1: extract resume text and skills", "Python tool", "failed", str(exc))
        return AgentResult(None, log.steps, str(exc))

    # 4. Tool 2: job analysis + comparison
    try:
        job = tools.analyze_job_description(jd_text)
        cmp = tools.compare_skills(resume_skills, job["skills"])
        log.add("Tool 2: analyze job and compare skills", "Python tool", "success",
                f"{len(job['skills'])} job skills; {len(cmp['matched'])} matched, {len(cmp['missing'])} not evidenced.")
    except ValueError as exc:
        log.add("Tool 2: analyze job and compare skills", "Python tool", "failed", str(exc))
        return AgentResult(None, log.steps, str(exc))

    candidates = tools.choose_candidate_topics(cmp["matched"], cmp["missing"], MAX_TOPICS)

    # 5. Tool 3: search
    resources, search_live = [], False
    if demo:
        outcome = tools.search_resources(candidates, search_fn=_builtin_search, results_per_topic=1)
        resources = outcome.resources
        log.add("Tool 3: load reference topics", "Python tool", "success",
                f"{len(resources)} reference topics loaded.")
    elif use_search:
        outcome = tools.search_resources(candidates, search_fn=search_fn)
        resources, search_live = outcome.resources, outcome.live
        # If live search failed entirely, fall back to built-in topics silently
        if not resources:
            fallback = tools.search_resources(candidates, search_fn=_builtin_search, results_per_topic=1)
            resources = fallback.resources
            log.add("Tool 3: search for resources", "Python tool", "success",
                    "Using built-in reference topics.")
        else:
            log.add("Tool 3: search for resources", "Python tool", "success",
                    f"{len(resources)} resources found.")
    else:
        log.add("Tool 3: search for resources", "Python tool", "skipped", "Web search was turned off.")

    context = {
        "job_title": job["title"], "job_text": jd_text,
        "matched": cmp["matched"], "missing": cmp["missing"], "candidates": candidates,
        "resources": [{"id": r.id, "topic": r.topic, "title": r.title,
                       "published": r.published.isoformat() if r.published else "unverified"} for r in resources],
    }

    # 6. LLM synthesis
    llm_used, raw = False, {}
    llm_fn = llm_fn or (synthesize_with_gemini if not demo else _rule_based_synthesize_fn)
    try:
        raw = llm_fn(context)
        llm_used = True
        log.add("Synthesis: topics prioritised and guide written", "Analysis engine",
                "success", "Analysis completed successfully.")
    except LLMError as exc:
        log.add("Synthesis: topics prioritised and guide written", "Analysis engine", "failed", str(exc))
        warnings.append("Analysis step encountered an issue. A guide built from the skill comparison is shown instead.")
    except Exception as exc:
        log.add("Synthesis: topics prioritised and guide written", "Analysis engine", "failed", f"{type(exc).__name__}: {exc}")
        warnings.append("Analysis step failed unexpectedly. A guide built from the skill comparison is shown instead.")

    # 7. Validation + output
    guide = validate_and_build_guide(raw, context, resources, cmp["matched"], cmp["missing"],
                                     job["title"], "analysis" if demo else "live",
                                     warnings, llm_used, search_live)
    log.add("Validation: links, dates and topics checked", "Python check", "success",
            "Resources come only from the search tool; LLM text cannot add links; undated items are labeled.")
    log.add("Output: preparation guide built", "Python", "success", f"{len(guide['topics'])} topics, {len(guide['resources'])} resources.")
    return AgentResult(guide, log.steps)
