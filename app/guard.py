"""Faithfulness guard: every load-bearing claim in the tailored resume must
trace back to the facts file. Violations raise UnfaithfulError."""
import re


class UnfaithfulError(ValueError):
    pass


def _norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def _numbers(text):
    return set(re.findall(r"\d+(?:\.\d+)?%?", str(text)))


def check(tailored, facts):
    """Raises UnfaithfulError on the first claim not supported by facts."""
    fact_skills = {_norm(s) for s in facts["skills"]}
    fact_companies = {_norm(j["company"]) for j in facts["experience"]}
    fact_projects = {_norm(p.get("name", "")) for p in facts.get("projects", [])}
    fact_degrees = {_norm(e["degree"]) for e in facts["education"]}
    fact_schools = {_norm(e["school"]) for e in facts["education"]}

    # every number anywhere in the source bullets/summary, as the allowed set
    allowed_numbers = set()
    source_texts = list(facts.get("summary_points", []))
    for job in facts["experience"]:
        source_texts += job["bullets"] + [job["role"]]
    for proj in facts.get("projects", []):
        source_texts += proj.get("bullets", [])
    for t in source_texts:
        allowed_numbers |= _numbers(t)

    # 1. skills must be a subset of facts.skills
    for skill in tailored.get("skills", []):
        if _norm(skill) not in fact_skills:
            raise UnfaithfulError(f"skill not in facts: {skill!r}")

    # 2. employers/roles/projects/education must exist in facts
    for job in tailored.get("experience", []):
        if _norm(job.get("company", "")) not in fact_companies:
            raise UnfaithfulError(f"company not in facts: {job.get('company')!r}")
        match = next(j for j in facts["experience"]
                     if _norm(j["company"]) == _norm(job["company"]))
        if _norm(job.get("role", "")) != _norm(match["role"]):
            raise UnfaithfulError(
                f"role changed for {job['company']!r}: {job.get('role')!r} != {match['role']!r}")
    for proj in tailored.get("projects", []):
        if _norm(proj.get("name", "")) not in fact_projects:
            raise UnfaithfulError(f"project not in facts: {proj.get('name')!r}")
    for edu in tailored.get("education", []):
        if _norm(edu.get("degree", "")) not in fact_degrees \
                or _norm(edu.get("school", "")) not in fact_schools:
            raise UnfaithfulError(f"education entry not in facts: {edu!r}")

    # 3. every number in the output must exist in the source facts
    out_texts = [tailored.get("summary", "")]
    for job in tailored.get("experience", []):
        out_texts += job.get("bullets", [])
    for proj in tailored.get("projects", []):
        out_texts += proj.get("bullets", [])
    for t in out_texts:
        for n in _numbers(t) - allowed_numbers:
            raise UnfaithfulError(f"number {n!r} in output does not appear in facts")

    return True
