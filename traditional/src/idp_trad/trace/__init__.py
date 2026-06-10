"""Per-step tracing for the traditional pipeline.

Opt-in instrumentation: when a `Tracer` is handed to the `Pipeline`, every step
(ingest → preprocess → extract → reading_order → serialize) records its timing,
a structured summary, and on-disk artifacts. When no tracer is given the pipeline
runs exactly as before with zero overhead.
"""

from idp_trad.trace.models import DocumentTrace, PageTraceRecord, StepRecord
from idp_trad.trace.tracer import Tracer

__all__ = ["DocumentTrace", "PageTraceRecord", "StepRecord", "Tracer"]
