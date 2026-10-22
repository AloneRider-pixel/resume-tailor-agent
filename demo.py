"""Offline demo: tailor the sample facts file to a JD, guard it, render LaTeX,
compile a PDF when pdflatex works on this machine."""
import os

os.environ.setdefault("AGENT_LLM", "mock")

from app import facts as facts_mod
from app import guard, latex, tailor
from app.llm import LLMClient
import json

JD = ("Senior Backend Engineer - Python/FastAPI. Must have PostgreSQL and Docker "
      "experience. Bonus: measurable latency improvements and AWS exposure.")


class SelectorMock:
    name = "demo/offline-deterministic"
    def available(self): return True
    def complete(self, prompt):
        facts = json.loads(prompt.split("FACTS (JSON):", 1)[1].split("JOB DESCRIPTION:")[0])
        jd_low = prompt.split("JOB DESCRIPTION:", 1)[1].lower()
        skills = [s for s in facts["skills"] if s.lower() in jd_low]
        skills += [s for s in facts["skills"] if s not in skills]
        return json.dumps({
            "summary": facts["summary_points"][0] + " Focused on Python, FastAPI, and "
                       "measurable API-latency wins.",
            "skills": skills,
            "experience": facts["experience"],
            "education": facts["education"],
            "projects": facts.get("projects", []),
        })


if __name__ == "__main__":
    facts = facts_mod.load_facts("facts.example.yaml")
    tailored, provider = tailor.tailor(facts, JD, LLMClient(providers=[SelectorMock()]))
    guard.check(tailored, facts)
    print(f"provider: {provider}")
    print(f"summary : {tailored['summary']}")
    print(f"skills  : {', '.join(tailored['skills'])}")
    print("guard   : all claims verified against facts.example.yaml")
    tex = latex.render_latex(tailored, facts)
    with open("resume_tailored.tex", "w") as fh:
        fh.write(tex)
    print("wrote   : resume_tailored.tex")
    try:
        pdf = latex.compile_pdf(tex, ".")
        print(f"wrote   : {pdf}")
    except RuntimeError as exc:
        print(f"pdf     : skipped ({exc})")
