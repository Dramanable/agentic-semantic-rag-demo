"""Command line entry point: `python -m app.presentation.evaluation_cli` (see `make eval`).

Indexes a folder of documents in a throw-away in-memory store, runs the question set through the real
workflow (the configured embeddings and LLM) and prints retrieval and confidence metrics.
"""

import argparse
import json
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from app.application.evaluation import EvalCase, EvalReport, evaluate
from app.infrastructure.container import build_container
from app.infrastructure.observability import configure_logging
from app.infrastructure.settings import Settings


def load_cases(path: Path) -> list[EvalCase]:
    return [EvalCase(item["question"], item["expected_source"]) for item in json.loads(path.read_text(encoding="utf-8"))]


def format_report(report: EvalReport) -> str:
    lines = [f"{'':2}{'question':52} {'expected':14} {'best source':14} {'confidence':>14} {'ms':>7}"]
    for r in report.results:
        mark = "ok" if r.correct else "KO"
        best = r.sources[0] if r.sources else "- (abstained)"
        conf = f"{r.confidence.level} {r.confidence.score:.2f}"
        lines.append(f"{mark:2}{r.case.question[:52]:52} {r.case.expected_source or '(none)':14} {best:14} {conf:>14} {r.latency_ms:7.0f}")
    lines += [
        "",
        f"Retrieval hit rate     {report.hit_rate:6.0%}   (expected source found, {report.answerable} answerable questions)",
        f"Mean reciprocal rank   {report.mrr:6.2f}   (1.00 = expected source always ranked first)",
        f"Abstention rate        {report.abstention_rate:6.0%}   (no answer when documents cannot answer, {report.unanswerable} questions)",
        f"Overall accuracy       {report.accuracy:6.0%}",
        f"Mean confidence        answerable {report.mean_confidence_answerable:.2f} | unanswerable {report.mean_confidence_unanswerable:.2f} | gap {report.confidence_gap:+.2f}",
        "Accuracy by confidence level (is the confidence trustworthy?):",
    ]
    for level in ("high", "medium", "low", "none"):
        if level in report.accuracy_by_level:
            correct, total = report.accuracy_by_level[level]
            lines.append(f"  {level:7} {correct}/{total} correct")
    lines.append(f"Mean latency           {report.mean_latency_ms:6.0f} ms per question")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the RAG on a question set.")
    parser.add_argument("--documents", type=Path, required=True, help="folder of .md/.txt files to index")
    parser.add_argument("--dataset", type=Path, required=True, help="JSON list of {question, expected_source}")
    parser.add_argument("--json", type=Path, help="also write the full report as JSON")
    parser.add_argument("--fail-under", type=float, default=0.0, help="exit 1 if overall accuracy is below this (0..1)")
    args = parser.parse_args(argv)

    configure_logging("WARNING")
    with tempfile.TemporaryDirectory() as scratch:
        settings = Settings(vector_store_provider="memory", documents_path=scratch)
        container = build_container(settings)
        files = sorted(p for p in args.documents.iterdir() if p.suffix in {".md", ".txt"})
        for path in files:
            container.ingest(path.name, path.read_text(encoding="utf-8"))
        print(f"Indexed {len(files)} documents | LLM: {settings.llm_provider} | embeddings: {settings.embeddings_provider}\n")
        report = evaluate(container.ask, load_cases(args.dataset))

    print(format_report(report))
    if args.json:
        args.json.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if report.accuracy >= args.fail_under else 1


if __name__ == "__main__":
    sys.exit(main())
