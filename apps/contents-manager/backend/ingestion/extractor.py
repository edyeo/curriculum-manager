"""Ontology-Aware Extractor — raw_text → ExtractionResult"""
import os
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
_ONTOLOGY_CANDIDATES = [
    Path(os.getenv("ONTOLOGY_PATH", "/app/data/ontology.yaml")),
    Path("/app/shared/ontology.yaml"),
    Path("agent-platform/shared/ontology.yaml"),
    Path("../../agent-platform/shared/ontology.yaml"),
]


class ExtractedNode(BaseModel):
    name: str
    type: str
    depth: int
    description: str
    parent_name: str | None = None
    source_excerpt: str = ""


class ExtractedEdge(BaseModel):
    source_name: str
    target_name: str
    relation: str
    basis: str
    source_excerpt: str = ""


class ExtractionResult(BaseModel):
    nodes: list[ExtractedNode]
    edges: list[ExtractedEdge]
    extraction_notes: str = ""


def _ontology_text() -> str:
    for p in _ONTOLOGY_CANDIDATES:
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError(
        "ontology.yaml not found. Set ONTOLOGY_PATH env var or mount at /app/data/ontology.yaml"
    )


_SYSTEM_TEMPLATE = """\
You are a knowledge graph extraction assistant.

Extract entities (nodes) and relations (edges) from the given text,
strictly following the ontology definition below.

## Ontology
```yaml
{ontology}
```

{subject_block}\
## Extraction Rules
1. Only use entity types defined in the ontology: System, Seed, Concept, TechStack.
2. Only use relation types defined in the ontology; respect valid_pairs.
3. Seed names must NOT contain specific technical solutions (anti_solution constraint).
   - Focus on problem spaces, tradeoffs, phenomena.
   - Bad: "Checkpointing", "Load Balancing"
   - Good: "Throughput vs. Latency Tradeoff", "State Divergence under Distributed Failures"
4. Assign depth 1–3 by abstraction level (1=high-level, 3=specific/concrete).
5. Set parent_name to the parent entity name within the same type, or null for depth=1.
6. source_excerpt: short quote from the text that justifies this extraction.
7. extraction_notes: briefly explain what you filtered out and why (including off-topic items).

Only extract entities clearly supported by the text.\
"""

_SUBJECT_BLOCK = """\
## Target Subject
This ingestion targets the subject **"{name}"**.
Description: {description}

Only extract entities that are relevant to this subject's scope.
Discard entities that are clearly off-topic for this subject, and note them in extraction_notes.

"""


def extract(raw_text: str, subject_name: str | None = None, subject_description: str | None = None) -> ExtractionResult:
    ontology = _ontology_text()
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if subject_name:
        desc = subject_description or "(no description provided)"
        subject_block = _SUBJECT_BLOCK.format(name=subject_name, description=desc)
    else:
        subject_block = ""

    completion = client.beta.chat.completions.parse(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_TEMPLATE.format(ontology=ontology, subject_block=subject_block)},
            {"role": "user", "content": f"Extract from the following text:\n\n---\n{raw_text}\n---"},
        ],
        response_format=ExtractionResult,
        temperature=0.3,
    )
    return completion.choices[0].message.parsed
