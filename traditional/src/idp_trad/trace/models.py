"""★ FROZEN CONTRACT — trace record models.

These are the ground-truth shapes that the Tracer writes to `trace.json` and that
`trace/report.py` renders. Phase-4 feature agents MUST NOT modify this file; if a
field is missing, report it as a blocker.

Design notes:
- `StepRecord.summary` is a free-form dict of the step's key facts (deskew angle,
  region counts, the extraction path that fired, etc.). Keep values JSON-serialisable
  (str/int/float/bool/list/dict) so `trace.json` round-trips.
- `artifacts` are relative paths (POSIX-style) under the document's trace dir, so a
  trace folder is portable / inspectable on its own.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Canonical step names, in pipeline order. Kept as a tuple so callers can validate.
STEP_NAMES = ("ingest", "preprocess", "extract", "reading_order", "serialize")


class Artifact(BaseModel):
    """One dumped file belonging to a step."""

    kind: str  # e.g. "preprocessed_image", "layout_overlay", "structure_raw", "block_crop"
    path: str  # relative to the document trace dir (POSIX separators)
    label: str = ""  # short human description


class StepRecord(BaseModel):
    """A single pipeline step's trace."""

    step: str
    latency_s: float = 0.0
    summary: dict = Field(default_factory=dict)
    artifacts: list[Artifact] = Field(default_factory=list)
    error: str | None = None


class PageTraceRecord(BaseModel):
    page: int = 0
    engine: str = ""
    total_latency_s: float = 0.0
    n_blocks: int = 0
    steps: list[StepRecord] = Field(default_factory=list)

    def step(self, name: str) -> StepRecord | None:
        for s in self.steps:
            if s.step == name:
                return s
        return None


class DocumentTrace(BaseModel):
    """The full per-document trace, serialised to `trace.json`."""

    document_id: str
    source_path: str = ""
    output_dir: str = ""
    pages: list[PageTraceRecord] = Field(default_factory=list)
