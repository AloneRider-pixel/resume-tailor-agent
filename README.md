# Resume Tailor Agent

Tailors a resume to a job posting - truthfully. The ONLY source of content is a
facts file you provide; a faithfulness guard rejects anything the LLM invents.
Output is LaTeX (compiled to PDF when pdflatex is available).

## What it does

- `POST /tailor {"jd_text": "...", "compile_pdf": false}` - loads `facts.yaml`
  (`FACTS_PATH`), asks the LLM to SELECT, ORDER, and lightly rephrase facts for the
  JD (never to invent), verifies the result, returns resume JSON + LaTeX (+ PDF path).
- `GET /health` - provider + facts-file status.

## The faithfulness guard (the point of this project)

`app/guard.py` rejects a tailored resume when any of these fail:

1. **Skills** must be a subset of `facts.skills`.
2. **Companies** must exist in `facts.experience`; **roles** must match the facts
   exactly (no title inflation); projects and education likewise.
3. **Numbers** - every number in the output (200k, 35%, 99.9%, ...) must appear
   verbatim in the source facts. No invented metrics.

A violation returns HTTP 422 with the exact claim that failed. Rephrasing is fine;
new facts are not.

## Facts file

`facts.example.yaml` shows the shape (a fictional sample person). Copy it to
`facts.yaml` and fill in your own verified facts. If it is not in the file,
it will not be in the resume.

## LLM: free providers with retry + fallback

Groq (`GROQ_API_KEY`) -> Gemini (`GEMINI_API_KEY`) -> local Ollama -> offline mock
(selector that orders facts by JD keyword overlap, no invention).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp facts.example.yaml facts.yaml   # then edit it
export GROQ_API_KEY=...            # or Gemini/Ollama, or skip for mock
uvicorn app.main:app --reload
```

## Demo + tests

```bash
python demo.py    # tailors the sample facts to a JD, guards, renders .tex, compiles .pdf when possible
pytest tests -q   # 10 tests: facts validation, guard (5 attack cases), LaTeX escaping/structure, real pdflatex compile when available
```

Verified locally: guard passes honest output and rejects an invented skill
(Kubernetes), an invented company (Google), an inflated title, and an invented
metric (500%) - each with a specific error. LaTeX renders with correct escaping.
The pdflatex compile test runs where pdflatex works (it auto-skips with the reason
in restricted environments); the .tex structure is validated either way.

## Honest limitations

- The guard checks numbers, names, titles, and skills; it cannot prove a rephrased
  sentence keeps its meaning - that is why rephrasing is restricted to "light".
- PDF compilation needs a local TeX install; the API always returns the .tex so any
  machine (or Overleaf) can compile it.
