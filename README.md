# CareerPilot Mini

A resume-based interview preparation agent built with Python and Streamlit.

Upload a PDF resume, paste a job description, and get a personalised interview preparation guide — including skill gap analysis, prioritised topics, preparation strategy, practice questions, and curated resources — downloadable as a Word document.

---

## How it works

| Step | What runs | What it does |
|------|-----------|--------------|
| 1 | Python (PyMuPDF) | Extracts text and detects skills from your resume PDF |
| 2 | Python | Parses the job description, identifies required skills, compares against resume |
| 3 | DuckDuckGo search | Fetches relevant interview prep resources (no API key needed) |
| 4 | Gemini LLM *(optional)* | Prioritises topics, writes strategy and practice questions |
| 5 | Python | Validates output, builds the guide, exports DOCX |

The app works fully without a Gemini API key — it uses built-in skill-analysis rules for synthesis. Add a key to unlock AI-generated topic ranking, strategy, and questions.

---

## Project structure

```
app.py                        Streamlit UI
careerpilot/
  config.py                   Settings and .env loading
  tools.py                    Deterministic tools: PDF, skills, comparison, search
  llm.py                      Gemini integration + rule-based fallback
  agent.py                    Orchestration and workflow log
  report.py                   DOCX export
sample_data/
  sample_resume.pdf           Fictional sample resume
  sample_job_description.txt  Fictional sample job description
tests/
  conftest.py
  test_careerpilot.py
requirements.txt
.env.example
```

---

## Setup (Windows)

### 1. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> If PowerShell blocks scripts: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment

```powershell
copy .env.example .env
```

Open `.env` and add your Gemini API key (optional — the app works without it):

```
GEMINI_API_KEY=your_key_here
```

Get a free key at https://aistudio.google.com/apikey

### 4. Run the app

```powershell
streamlit run app.py
```

Opens at http://localhost:8501

### 5. Run tests

```powershell
python -m pytest -v
```

No API key or internet connection required for tests.

---

## Quick start (no setup)

1. Tick **"Use sample resume & job description"** in the sidebar
2. Click **Generate preparation guide**
3. Download the Word document

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `py` not recognised | Install Python from python.org and tick "Add Python to PATH" |
| PowerShell scripts disabled | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `streamlit` not recognised | Activate the virtual environment first |
| PDF has no extractable text | Use a text-based PDF (exported from Word/Google Docs, not a scan) |

---

## Tech stack

- **Streamlit** — UI
- **PyMuPDF** — PDF text extraction
- **DuckDuckGo Search (ddgs)** — resource discovery, no API key needed
- **Google Gemini** — optional AI synthesis
- **python-docx** — DOCX export
- **pytest** — testing
