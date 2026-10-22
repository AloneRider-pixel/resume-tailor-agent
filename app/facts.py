"""Load and validate the facts file - the ONLY source of resume content."""
import yaml

REQUIRED = ["name", "email", "skills", "experience", "education"]


class FactsError(ValueError):
    pass


def load_facts(path):
    with open(path) as fh:
        facts = yaml.safe_load(fh)
    if not isinstance(facts, dict):
        raise FactsError("facts file must be a YAML mapping")
    for key in REQUIRED:
        if key not in facts:
            raise FactsError(f"facts file missing required key: {key}")
    for job in facts["experience"]:
        for key in ("company", "role", "start", "bullets"):
            if key not in job:
                raise FactsError(f"experience entry missing {key!r}: {job}")
    if not facts["skills"]:
        raise FactsError("skills list may not be empty")
    return facts
