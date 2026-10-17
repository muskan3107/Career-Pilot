"""Deterministic Python tools used by the agent.

None of these functions call an LLM. They always behave the same for the same
input, which makes them easy to test. The LLM is only used later, in llm.py,
for reasoning and writing.
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime

import pymupdf  # PyMuPDF

from .config import RECENCY_YEARS, RESULTS_PER_TOPIC

# canonical skill name -> aliases that count as a mention (case-insensitive)
SKILL_TAXONOMY = {
    "Python": ["python"],
    "Java": ["java"],
    "JavaScript": ["javascript", "ecmascript"],
    "TypeScript": ["typescript"],
    "C++": ["c++"],
    "C#": ["c#"],
    "Go": ["golang"],
    "Rust": ["rust"],
    "SQL": ["sql", "postgresql", "mysql", "sqlite"],
    "NoSQL": ["nosql", "mongodb", "dynamodb", "cassandra"],
    "React": ["react", "react.js", "reactjs"],
    "Node.js": ["node.js", "nodejs"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi"],
    "Spring Boot": ["spring boot", "springboot", "spring framework"],
    "REST APIs": ["rest api", "rest apis", "restful", "restful apis"],
    "GraphQL": ["graphql"],
    "Microservices": ["microservices", "microservice"],
    "System Design": ["system design", "distributed systems", "scalability"],
    "Data Structures & Algorithms": ["data structures", "algorithms", "dsa"],
    "Object-Oriented Programming": ["oop", "object-oriented", "object oriented"],
    "Git": ["git", "github", "gitlab"],
    "Docker": ["docker", "containers", "containerization"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "CI/CD": ["ci/cd", "cicd", "jenkins", "github actions"],
    "Linux": ["linux", "unix"],
    "Unit Testing": ["unit testing", "unit tests", "pytest", "junit", "tdd"],
    "Agile/Scrum": ["agile", "scrum"],
    "Machine Learning": ["machine learning", "scikit-learn", "sklearn"],
    "Deep Learning": ["deep learning", "pytorch", "tensorflow", "keras"],
    "NLP": ["nlp", "natural language processing"],
    "Pandas/NumPy": ["pandas", "numpy"],
    "Data Analysis": ["data analysis", "data analytics"],
    "HTML/CSS": ["html", "css", "html5", "css3"],
    "Redis": ["redis"],
    "Kafka": ["kafka"],
    "Operating Systems": ["operating systems", "operating system"],
    "Computer Networks": ["computer networks", "tcp/ip"],
    "DBMS": ["dbms", "database design", "database management"],
    "Security": ["cybersecurity", "owasp", "authentication", "encryption"],
}

MIN_JD_CHARS = 40


# ---------------------------------------------------------------- helpers
def _alias_pattern(alias):
    # Lookarounds instead of \b so "C++", "C#" and "Node.js" match correctly,
    # while "Java" does NOT match inside "JavaScript".
    return re.compile(r"(?<![A-Za-z0-9+#])" + re.escape(alias) + r"(?![A-Za-z0-9+#])", re.IGNORECASE)


_PATTERNS = {
    skill: [_alias_pattern(a) for a in aliases] for skill, aliases in SKILL_TAXONOMY.items()
}


def count_skill_mentions(text):
    """Return {skill: number_of_mentions} for skills found in text."""
    counts = {}
    for skill, patterns in _PATTERNS.items():
        n = sum(len(p.findall(text)) for p in patterns)
        if n:
            counts[skill] = n
    return counts


# ------------------------------------------------------- Tool 1: resume
def extract_resume_text(pdf_bytes):
    """Extract plain text from a PDF given as bytes. Raises ValueError on bad input."""
    if not pdf_bytes:
        raise ValueError("No resume file was provided.")
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # corrupted file, not a PDF, etc.
        raise ValueError(f"Could not read the file as a PDF: {exc}") from exc
    try:
        text = "\n".join(page.get_text() for page in doc).strip()
    finally:
        doc.close()
    if len(text) < 20:
        raise ValueError(
            "The PDF contains no extractable text (it may be a scanned image). "
            "Please upload a text-based PDF."
        )
    return text


def extract_resume_skills(resume_text):
    """Return the list of taxonomy skills evidenced in the resume text."""
    return sorted(count_skill_mentions(resume_text))


# ------------------------------------------------- Tool 2: job analysis
def analyze_job_description(jd_text):
    """Return {'title': str, 'skills': [skills ordered by importance]}.

    Importance = how often the skill is mentioned (ties: earlier mention wins).
    Raises ValueError for an empty/too-short/unusable job description.
    """
    jd_text = (jd_text or "").strip()
    if not jd_text:
        raise ValueError("The job description is empty.")
    if len(jd_text) < MIN_JD_CHARS:
        raise ValueError("The job description is too short to analyze. Paste the full text.")

    counts = count_skill_mentions(jd_text)
    if not counts:
        raise ValueError(
            "No recognizable software engineering skills were found in the job description."
        )

    def first_pos(skill):
        positions = [m.start() for p in _PATTERNS[skill] for m in p.finditer(jd_text)]
        return min(positions)

    ordered = sorted(counts, key=lambda s: (-counts[s], first_pos(s)))
    first_line = next((ln.strip() for ln in jd_text.splitlines() if ln.strip()), "")
    title = first_line if 0 < len(first_line) <= 80 else "Software Engineering role (title not detected)"
    return {"title": title, "skills": ordered, "mention_counts": counts}


def compare_skills(resume_skills, job_skills):
    """Split job skills into matched / not evidenced in resume (job order preserved)."""
    resume_set = set(resume_skills)
    matched = [s for s in job_skills if s in resume_set]
    missing = [s for s in job_skills if s not in resume_set]
    return {"matched": matched, "missing": missing}


def choose_candidate_topics(matched, missing, max_topics=8):
    """Gaps first (highest priority), then matched skills to refresh."""
    return (missing + matched)[:max_topics]


# --------------------------------------------------- Tool 3: web search
@dataclass
class Resource:
    id: int
    topic: str
    title: str
    url: str
    published: date | None = None
    date_note: str = "Publication date not verified"


@dataclass
class SearchOutcome:
    resources: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    live: bool = False


def _parse_date(value):
    """Accept a date/datetime or an ISO-like string (YYYY-MM-DD...). Else None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    m = re.match(r"\s*(\d{4})[-/](\d{2})[-/](\d{2})", str(value))
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    return None


def _date_from_url(url):
    """Only accepts clear /YYYY/MM/ patterns in the URL. Returns date or None."""
    m = re.search(r"/(20\d{2})/(0[1-9]|1[0-2])(?:/|$)", url or "")
    if m:
        return date(int(m[1]), int(m[2]), 1)
    return None


def _ddgs_search(query, max_results):
    """Default search function: DuckDuckGo via the `ddgs` package (no API key)."""
    from ddgs import DDGS

    return list(DDGS().text(query, max_results=max_results))


def search_resources(topics, search_fn=None, today=None, results_per_topic=RESULTS_PER_TOPIC):
    """Look up public interview-prep resources for each topic.

    `search_fn(query, max_results)` must return dicts with 'title' and 'href'
    (optionally 'date'). It is injectable so tests can run without internet.
    Nothing is invented: if search fails or returns nothing, the outcome has
    zero resources and a warning.
    """
    search_fn = search_fn or _ddgs_search
    today = today or date.today()
    cutoff = date(today.year - RECENCY_YEARS, today.month, min(today.day, 28))
    outcome = SearchOutcome()
    seen_urls = set()
    failures = 0

    for topic in topics:
        query = f"{topic} software engineer interview questions"
        try:
            raw = search_fn(query, results_per_topic + 2)
        except Exception as exc:
            failures += 1
            outcome.warnings.append(f"Search failed for '{topic}': {type(exc).__name__}")
            continue
        added = 0
        for item in raw or []:
            url = (item.get("href") or item.get("url") or "").strip()
            title = (item.get("title") or "").strip()
            if not url.startswith(("http://", "https://")) or not title or url in seen_urls:
                continue
            pub = _parse_date(item.get("date"))
            note = "Date from search metadata"
            if pub is None:
                pub = _date_from_url(url)
                note = "Date inferred from URL pattern (approximate)"
            if pub is None:
                note = "Publication date not verified"
            elif pub < cutoff:
                continue  # verifiably older than the recency window -> skip
            seen_urls.add(url)
            outcome.resources.append(
                Resource(id=len(outcome.resources) + 1, topic=topic, title=title, url=url,
                         published=pub, date_note=note)
            )
            added += 1
            if added >= results_per_topic:
                break

    outcome.live = bool(outcome.resources)
    # Internal warnings are kept only for the workflow log, not for the user UI.
    # We intentionally do not surface search-failure or date-verification messages.
    return outcome
