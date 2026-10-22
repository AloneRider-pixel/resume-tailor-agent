"""Ask the LLM to SELECT and ORDER facts for a job description - never to invent.

The prompt hands the LLM the full facts file as JSON and demands a structured
selection. app/guard.py then verifies the output against the facts."""
import json
import re

TAILOR_PROMPT = """TAILOR_JSON:
You are a resume tailoring engine. You may ONLY select, order, and lightly rephrase
content from the FACTS below. Never invent employers, roles, dates, skills, or numbers.
FACTS (JSON):
{facts}

JOB DESCRIPTION:
{jd}

Reply with ONE JSON object (no prose, no markdown):
{{
  "summary": "2-3 sentences tailored to the JD, using only summary_points and skills from FACTS",
  "skills": ["subset of FACTS.skills, ordered by relevance to the JD"],
  "experience": [{{"company": "...", "role": "...", "start": "...", "end": "...",
                   "bullets": ["bullets from FACTS, at most lightly rephrased, numbers unchanged"]}}],
  "education": [{{"degree": "...", "school": "...", "year": "..."}}],
  "projects": [{{"name": "...", "bullets": ["..."]}}]
}}
"""


def extract_json(text):
    if not text:
        return None
    cleaned = re.sub(r"```(?:json)?", "", text)
    start = cleaned.find("{")
    if start == -1:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _valid(out):
    return isinstance(out.get("summary"), str) and isinstance(out.get("skills"), list) \
        and isinstance(out.get("experience"), list) and isinstance(out.get("education"), list)


def tailor(facts, jd, llm, retries=1):
    prompt = TAILOR_PROMPT.format(facts=json.dumps(facts, default=str), jd=jd)
    for _ in range(retries + 1):
        raw = llm.complete(prompt)
        out = extract_json(raw)
        if out and _valid(out):
            out.setdefault("projects", [])
            return out, llm.active.name
        prompt += "\nPrevious reply was not valid JSON. Reply with JSON only."
    raise ValueError("LLM could not produce a valid tailored resume")
