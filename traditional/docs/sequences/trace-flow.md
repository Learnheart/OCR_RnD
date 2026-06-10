---
author: lytinh358@gmail.com
date: 2026-06-10
status: done
agents: traditional
summary: Sequence diagram of the per-step --trace flow through the traditional OCR pipeline.
---

# Sequence — `parse_one.py --trace`

How a single document flows when tracing is enabled. The `Tracer` is opt-in: when it is
`None` (the eval/batch default) the pipeline runs identically with zero trace overhead.

Accurate to `scripts/parse_one.py` + `src/idp_trad/pipeline.py` (`_process_page`),
`src/idp_trad/trace/tracer.py`, and `src/idp_trad/trace/artifacts.py`.

```mermaid
sequenceDiagram
    actor User
    participant CLI as parse_one.py (--trace)
    participant Tracer
    participant Pipe as Pipeline
    participant Pre as preprocess()
    participant Eng as PaddleStructureEngine
    participant Art as artifacts.dump_page
    participant FS as trace dir

    User->>CLI: parse_one.py <img> --trace [DIR]
    CLI->>Tracer: Tracer(DIR=results/traces)
    CLI->>Pipe: Pipeline(tracer=Tracer).process_file(img)

    Pipe->>Tracer: begin_document(doc_id) → creates <doc_id>/
    Pipe->>Tracer: add_page() → PageTraceRecord

    Note over Pipe: _process_page — steps each record timing + summary
    Pipe->>Pre: preprocess(image)  (deskew / denoise / enhance)
    Pre-->>Pipe: img, info (enhance gate result)
    Pipe->>Eng: parse(page)

    alt structure coverage poor
        Eng->>Eng: full-page PP-OCRv4 fallback
        Note right of Eng: last_meta.fallback_used = true (+ reason)
    else structure OK
        Eng->>Eng: PP-Structure layout + table→HTML
        Note right of Eng: last_meta.fallback_used = false
    end
    Eng-->>Pipe: blocks  (+ engine.last_meta: path / regions / fallback)

    Pipe->>Tracer: dump_page_artifacts(rec, original, preprocessed, blocks, last_meta)
    Tracer->>Art: dump_page(page_dir, …)
    Art->>FS: original.png, preprocessed.png
    Art->>FS: structure_raw.json (regions + fallback decision)
    Art->>FS: layout_overlay.png (bbox by type + reading-order #)
    Art->>FS: crops/<order>_<type>.png
    Art-->>Tracer: {step: [Artifact,…]} → attached to StepRecords

    Pipe-->>CLI: DocumentResult
    CLI->>CLI: document_to_md(doc)  → serialize step recorded
    CLI->>Tracer: write() → trace.json
    CLI->>FS: write_report(doc) → report.md (timing table + FALLBACK callout + regions)
    CLI-->>User: markdown on stdout + [trace] dir / pages / fallback count on stderr
```

## Notes

- The pipeline does **not** depend on the tracer module beyond accepting an optional
  `Tracer`. The engine merely exposes a read-only `last_meta` dict (path used, region
  count, fallback decision) — data exposure, not a tracer dependency.
- The **serialize** step is timed and recorded by the CLI (`parse_one.py`), since
  `document_to_md` is called there, not inside `Pipeline`.
- Artifact rendering (`idp_trad.trace.artifacts`) is lazy-imported and fully guarded:
  any failure is swallowed so tracing can never break a run.
