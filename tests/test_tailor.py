"""Offline tests + a real pdflatex compile (skipped if pdflatex missing)."""
import json
import os
import shutil

os.environ["AGENT_LLM"] = "mock"

import pytest

from app import facts as facts_mod
from app import guard, latex, tailor
from app.llm import LLMClient, MockProvider

FACTS = facts_mod.load_facts(os.path.join(os.path.dirname(__file__), "..", "facts.example.yaml"))
JD = ("We need a backend engineer with strong Python and FastAPI skills, PostgreSQL "
      "experience, and a track record of improving API latency. Docker is a plus.")


class SelectorMock(MockProvider):
    """Deterministic tailor: picks JD-relevant skills, first bullets, no invention."""
    def complete(self, prompt):
        facts = json.loads(prompt.split("FACTS (JSON):", 1)[1].split("JOB DESCRIPTION:")[0])
        jd_low = prompt.split("JOB DESCRIPTION:", 1)[1].lower()
        skills = [s for s in facts["skills"] if s.lower() in jd_low]
        skills += [s for s in facts["skills"] if s not in skills]
        out = {
            "summary": facts["summary_points"][0] + " Focused on Python and FastAPI.",
            "skills": skills,
            "experience": [{**j, "bullets": j["bullets"][:2]} for j in facts["experience"]],
            "education": facts["education"],
            "projects": facts.get("projects", []),
        }
        return json.dumps(out)


def _tailored():
    return tailor.tailor(FACTS, JD, LLMClient(providers=[SelectorMock()]))[0]


def test_facts_file_loads_and_validates():
    assert FACTS["name"] == "Aditya Sharma"
    assert len(FACTS["skills"]) >= 3
    with pytest.raises(facts_mod.FactsError):
        facts_mod.load_facts(os.path.join(os.path.dirname(__file__), "bad_facts.yaml"))


def test_tailor_and_guard_pass_on_honest_output():
    t = _tailored()
    assert guard.check(t, FACTS) is True
    assert "Python" in t["skills"]


def test_guard_rejects_invented_skill():
    t = _tailored()
    t["skills"].append("Kubernetes")  # not in facts
    with pytest.raises(guard.UnfaithfulError, match="skill"):
        guard.check(t, FACTS)


def test_guard_rejects_invented_company():
    t = _tailored()
    t["experience"][0]["company"] = "Google"
    with pytest.raises(guard.UnfaithfulError, match="company"):
        guard.check(t, FACTS)


def test_guard_rejects_changed_role():
    t = _tailored()
    t["experience"][0]["role"] = "Senior Backend Engineer"
    with pytest.raises(guard.UnfaithfulError, match="role"):
        guard.check(t, FACTS)


def test_guard_rejects_invented_number():
    t = _tailored()
    t["experience"][0]["bullets"][0] = "Improved throughput 500% through caching."
    with pytest.raises(guard.UnfaithfulError, match="number"):
        guard.check(t, FACTS)


def test_guard_allows_rephrase_with_same_numbers():
    t = _tailored()
    t["experience"][0]["bullets"][0] = \
        "Built a FastAPI order service processing 200k requests/day at 99.9% uptime."
    assert guard.check(t, FACTS) is True


def test_latex_renders_and_escapes():
    tex = latex.render_latex(_tailored(), FACTS)
    assert "\\documentclass" in tex and "\\end{document}" in tex
    assert "Aditya Sharma" in tex
    assert "99.9\\%" in tex  # % escaped
    assert "requests/day at" in tex


@pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdflatex not installed")
def test_real_pdf_compiles(tmp_path):
    try:
        pdf = latex.compile_pdf(latex.render_latex(_tailored(), FACTS), str(tmp_path))
    except RuntimeError as exc:
        pytest.skip(f"pdflatex present but unusable in this environment: {exc}")
    assert os.path.getsize(pdf) > 5000
    with open(pdf, "rb") as fh:
        assert fh.read(4) == b"%PDF"


def test_tex_is_structurally_sound():
    tex = latex.render_latex(_tailored(), FACTS)
    assert tex.count("\\begin{") == tex.count("\\end{")  # every environment closed
    assert tex.count("{") == tex.count("}")                  # balanced braces
    for ch in ["&", "#"]:                                    # no bare specials outside escapes
        assert all(tex[max(0, m - 1)] == "\\" for m in
                   (i for i, c in enumerate(tex) if c == ch))
