"""Human-readable Markdown report from a DocumentTrace (feature F1).

`render_report` turns the structured trace (the same data in `trace.json`) into a
Markdown document a human can skim: per-page step tables, the fallback decision
called out prominently, the regions table, and links to the dumped artifacts.

Artifact paths in a StepRecord are already relative (POSIX) to the document trace
dir, so the report — written at `<doc_dir>/report.md` — can link them directly.
"""

from __future__ import annotations

from pathlib import Path

from idp_trad.trace.models import DocumentTrace, PageTraceRecord, StepRecord

# Which summary keys to surface per step, in order. Anything else is ignored to
# keep the table readable (full detail lives in trace.json / structure_raw.json).
_STEP_FACT_KEYS: dict[str, tuple[str, ...]] = {
    "ingest": ("source_path", "width", "height", "channels"),
    "preprocess": ("deskew_deg", "denoised", "scale"),
    "extract": ("path_used", "struct_chars", "n_regions"),
    "reading_order": ("n_blocks",),
    "serialize": ("md_chars",),
}


def _md_escape(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _facts_cell(rec: StepRecord) -> str:
    keys = _STEP_FACT_KEYS.get(rec.step)
    summary = rec.summary or {}
    if keys:
        items = [(k, summary[k]) for k in keys if k in summary and summary[k] is not None]
    else:
        items = [
            (k, v)
            for k, v in summary.items()
            if k != "regions" and not isinstance(v, (list, dict)) and v is not None
        ]
    if not items:
        return ""
    return "; ".join(f"{k}={_md_escape(v)}" for k, v in items)


def _artifacts_cell(rec: StepRecord) -> str:
    if not rec.artifacts:
        return ""
    parts = []
    for a in rec.artifacts:
        label = a.label or Path(a.path).name
        parts.append(f"[{_md_escape(label)}]({a.path})")
    return "<br>".join(parts)


def _fallback_callout(page: PageTraceRecord) -> str:
    extract = page.step("extract")
    summary = (extract.summary if extract else {}) or {}
    if summary.get("fallback_used"):
        reason = summary.get("fallback_reason") or "unknown"
        return f"**⚠ FALLBACK: {_md_escape(reason)}**"
    path_used = summary.get("path_used") or "structure"
    return f"path: {_md_escape(path_used)}"


def _regions_table(page: PageTraceRecord) -> list[str]:
    extract = page.step("extract")
    summary = (extract.summary if extract else {}) or {}
    regions = summary.get("regions") or []
    if not regions:
        return []
    lines = [
        "",
        "**Regions**",
        "",
        "| order | type | bbox | preview |",
        "| ---: | --- | --- | --- |",
    ]
    for r in regions:
        order = r.get("reading_order", "")
        rtype = r.get("type", "")
        bbox = r.get("bbox", "")
        if isinstance(bbox, (list, tuple)):
            bbox = "[" + ", ".join(f"{float(v):.0f}" for v in bbox) + "]"
        preview = r.get("text_preview", "") or ""
        lines.append(
            f"| {_md_escape(order)} | {_md_escape(rtype)} | "
            f"{_md_escape(bbox)} | {_md_escape(preview)} |"
        )
    return lines


def _page_section(page: PageTraceRecord) -> list[str]:
    lines: list[str] = [
        "",
        f"## Page {page.page} — engine `{_md_escape(page.engine)}`",
        "",
        f"- total latency: {page.total_latency_s:.4f}s",
        f"- blocks: {page.n_blocks}",
        "",
        _fallback_callout(page),
        "",
        "| step | latency_s | facts | artifacts |",
        "| --- | ---: | --- | --- |",
    ]
    for rec in page.steps:
        err = f" (error: {_md_escape(rec.error)})" if rec.error else ""
        lines.append(
            f"| {_md_escape(rec.step)} | {rec.latency_s:.4f} | "
            f"{_facts_cell(rec)}{err} | {_artifacts_cell(rec)} |"
        )
    lines.extend(_regions_table(page))
    return lines


def render_report(doc_trace: DocumentTrace) -> str:
    """Render a DocumentTrace to a human-readable Markdown string."""
    n_pages = len(doc_trace.pages)
    n_fallback = sum(
        1
        for p in doc_trace.pages
        if (p.step("extract").summary if p.step("extract") else {}).get("fallback_used")
    )
    lines: list[str] = [
        f"# Trace report — {_md_escape(doc_trace.document_id)}",
        "",
        f"- source: `{_md_escape(doc_trace.source_path)}`",
        f"- output dir: `{_md_escape(doc_trace.output_dir)}`",
        f"- pages: {n_pages}",
        f"- fallback pages: {n_fallback}",
    ]
    for page in doc_trace.pages:
        lines.extend(_page_section(page))
    lines.append("")
    return "\n".join(lines)


def write_report(doc_trace: DocumentTrace, out_path: Path) -> Path:
    """Render and write the Markdown report; return the written path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_report(doc_trace), encoding="utf-8")
    return out_path
