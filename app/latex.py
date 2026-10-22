"""Render the tailored resume to LaTeX (and PDF when pdflatex is available)."""
import os
import shutil
import subprocess
import tempfile

SPECIALS = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
            "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(text):
    return "".join(SPECIALS.get(ch, ch) for ch in str(text))


def render_latex(tailored, facts):
    L = []
    L.append(r"\documentclass[11pt]{article}")
    L.append(r"\usepackage[margin=0.8in]{geometry}")
    L.append(r"\usepackage{enumitem}")
    L.append(r"\setlist{nosep}")
    L.append(r"\pagenumbering{gobble}")
    L.append(r"\begin{document}")
    L.append(r"\begin{center}")
    L.append(r"{\LARGE \textbf{%s}}\\" % esc(facts["name"]))
    contact = " | ".join(esc(x) for x in [facts.get("email", ""), facts.get("phone", ""),
                                          facts.get("location", "")] if x)
    L.append(contact)
    L.append(r"\end{center}")
    L.append(r"\section*{Summary}")
    L.append(esc(tailored["summary"]))
    L.append(r"\section*{Skills}")
    L.append(esc(", ".join(tailored["skills"])))
    L.append(r"\section*{Experience}")
    for job in tailored["experience"]:
        L.append(r"\noindent\textbf{%s} --- %s\hfill %s -- %s" % (
            esc(job["company"]), esc(job["role"]), esc(str(job["start"])), esc(str(job["end"]))))
        L.append(r"\begin{itemize}")
        for b in job["bullets"]:
            L.append(r"\item " + esc(b))
        L.append(r"\end{itemize}")
    if tailored.get("projects"):
        L.append(r"\section*{Projects}")
        for p in tailored["projects"]:
            L.append(r"\noindent\textbf{%s}" % esc(p["name"]))
            L.append(r"\begin{itemize}")
            for b in p.get("bullets", []):
                L.append(r"\item " + esc(b))
            L.append(r"\end{itemize}")
    L.append(r"\section*{Education}")
    for e in tailored["education"]:
        L.append(r"\noindent\textbf{%s}, %s\hfill %s\\" % (
            esc(e["degree"]), esc(e["school"]), esc(str(e["year"]))))
    L.append(r"\end{document}")
    return "\n".join(L) + "\n"


def compile_pdf(latex_source, out_dir=None):
    """Returns the PDF path. Raises RuntimeError when pdflatex is unavailable or fails."""
    if not shutil.which("pdflatex"):
        raise RuntimeError("pdflatex not installed; return the .tex and compile elsewhere")
    out_dir = out_dir or tempfile.mkdtemp(prefix="resume-")
    tex_path = os.path.join(out_dir, "resume.tex")
    with open(tex_path, "w") as fh:
        fh.write(latex_source)
    proc = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "resume.tex"],
        cwd=out_dir, capture_output=True, text=True, timeout=120)
    pdf = os.path.join(out_dir, "resume.pdf")
    if proc.returncode != 0 or not os.path.exists(pdf):
        raise RuntimeError(f"pdflatex failed: {proc.stdout[-1500:]}")
    return pdf
