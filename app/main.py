"""FastAPI surface for the resume tailor."""
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import facts as facts_mod
from . import guard, latex, tailor
from .llm import LLMClient

app = FastAPI(title="Resume Tailor Agent", version="1.0.0")
llm = LLMClient()

FACTS_PATH = os.getenv("FACTS_PATH", "facts.yaml")


class TailorRequest(BaseModel):
    jd_text: str = Field(..., min_length=20)
    compile_pdf: bool = False


@app.get("/health")
def health():
    return {"status": "ok", "provider": llm.active.name,
            "facts_file": os.path.exists(FACTS_PATH)}


@app.post("/tailor")
def tailor_resume(body: TailorRequest):
    if not os.path.exists(FACTS_PATH):
        raise HTTPException(400, f"facts file not found at {FACTS_PATH}")
    facts = facts_mod.load_facts(FACTS_PATH)
    try:
        tailored, provider = tailor.tailor(facts, body.jd_text, llm)
    except ValueError as exc:
        raise HTTPException(502, f"LLM failed to produce a valid resume: {exc}")
    try:
        guard.check(tailored, facts)
    except guard.UnfaithfulError as exc:
        raise HTTPException(422, f"LLM output rejected by the faithfulness guard: {exc}")
    tex = latex.render_latex(tailored, facts)
    result = {"provider": provider, "resume": tailored, "latex": tex, "pdf_path": None}
    if body.compile_pdf:
        try:
            result["pdf_path"] = latex.compile_pdf(tex)
        except RuntimeError as exc:
            result["pdf_error"] = str(exc)
    return result
