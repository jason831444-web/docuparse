# DocuParse Quality Evaluation Harness

This evaluation harness generates a representative local corpus, runs each
document through the current DocuParse pipeline, scores the output quality, and
produces both JSON and Markdown reports.

Use it to:

- spot weak titles, generic classifications, and brittle summaries
- catch malformed action items and inconsistent metadata
- compare a refinement run against a baseline before keeping changes

Typical flow:

```bash
cd /Users/yoonjaeseong/Desktop/projects/DocuParse/backend
./.venv/bin/python scripts/run_quality_eval.py --label baseline
# make a focused refinement
./.venv/bin/python scripts/run_quality_eval.py --label refined --compare-to eval/reports/latest.json
```

The harness stores:

- generated docs in `backend/eval/corpus/`
- run reports in `backend/eval/reports/`
- representative expectations in `backend/eval/specs/eval_documents.json`

The expectations are intentionally coarse. They do not hardcode exact text;
instead they define quality signals such as expected profiles, broad types,
keyword coverage, and anti-patterns to avoid.

