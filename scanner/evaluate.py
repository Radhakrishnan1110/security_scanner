from __future__ import annotations

import json
import re
from pathlib import Path


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", value.lower()))


def _score(finding: dict, truth: dict) -> float:
    searchable = f"{finding.get('type', '')} {finding.get('evidence', '')}".lower()
    aliases = truth["aliases"]
    phrase_hits = sum(alias.lower() in searchable for alias in aliases)
    title_overlap = len(_words(truth["title"]) & _words(searchable))
    return min(1.0, 0.5 * phrase_hits + 0.1 * title_overlap)


def evaluate(scan_path: Path, ground_truth_path: Path, output_path: Path, confirmed: dict[str, int] | None = None) -> dict:
    findings = json.loads(scan_path.read_text(encoding="utf-8"))["findings"]
    ground_truth = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    candidates = []
    for truth in ground_truth:
        ranked = sorted(
            (
                {"finding_index": index, "score": _score(finding, truth), "finding": finding}
                for index, finding in enumerate(findings)
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        candidates.append({"ground_truth": truth, "candidates": [item for item in ranked[:3] if item["score"] > 0]})

    confirmed = confirmed or {}
    invalid = {key: value for key, value in confirmed.items() if key not in {item["id"] for item in ground_truth} or not isinstance(value, int) or value >= len(findings)}
    if invalid:
        raise ValueError(f"Invalid confirmed matches: {invalid}")
    matched_ids = set(confirmed)
    result = {
        "scan": str(scan_path),
        "ground_truth": str(ground_truth_path),
        "ground_truth_count": len(ground_truth),
        "finding_count": len(findings),
        "confirmed_matches": confirmed,
        "confirmed_recall": len(matched_ids) / len(ground_truth) if ground_truth else 0,
        "unmatched_ground_truth": [item for item in ground_truth if item["id"] not in matched_ids],
        "candidate_matches_for_manual_review": candidates,
        "note": "Recall is final only after reviewing candidate matches. A finding may be confirmed against at most one ground-truth entry.",
    }
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
