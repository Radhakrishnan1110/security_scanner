from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .config import Settings
from .ingest import SourceChunk
from .models import LanguageModel, PromptBlockedError


FINDING_SCHEMA = """Return JSON only, in this exact shape:
{
  "findings": [
    {
      "type": "short vulnerability category",
      "location": "relative/path:line or relative/path:start-end",
      "severity": "low|medium|high|critical",
      "evidence": "specific risky behavior observed in the supplied code",
      "confidence": 0.0
    }
  ]
}
Do not report a finding unless the supplied code supports it. Do not invent paths or line numbers."""

SECURITY_TERMS = (
    "webview", "loadurl", "url", "intent", "provider", "receiver", "broadcast", "fileprovider", "file",
    "ssl", "certificate", "trust", "cognito", "aws", "password", "credential", "preference", "storage",
    "log", "javascript", "context", "exported", "upload",
)


@dataclass(frozen=True)
class Finding:
    type: str
    location: str
    severity: str
    evidence: str
    confidence: float


def _load_chunks(corpus_path: Path, limit: int) -> list[SourceChunk]:
    chunks: list[SourceChunk] = []
    with corpus_path.open(encoding="utf-8") as handle:
        for line in handle:
            chunks.append(SourceChunk(**json.loads(line)))
    def priority(chunk: SourceChunk) -> tuple[int, str]:
        haystack = f"{chunk.path}\n{chunk.content}".lower()
        score = sum(term in haystack for term in SECURITY_TERMS)
        if chunk.path == "AndroidManifest.xml":
            score += 100
        if chunk.path.endswith((".smali", ".java", ".kt")):
            score += 3
        return (-score, chunk.path)
    return sorted(chunks, key=priority)[:limit]


def _batches(items: list[SourceChunk], batch_size: int, max_chars: int) -> Iterable[list[SourceChunk]]:
    batch: list[SourceChunk] = []
    size = 0
    for item in items:
        if batch and (len(batch) >= batch_size or size + len(item.content) > max_chars):
            yield batch
            batch, size = [], 0
        batch.append(item)
        size += len(item.content)
    if batch:
        yield batch


def _extract_json(response: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.S)
    candidate = fenced.group(1) if fenced else response.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start, end = response.find("{"), response.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Model response did not contain JSON")
        return json.loads(response[start : end + 1])


def _validate_findings(payload: dict, known_paths: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    for item in payload.get("findings", []):
        if not isinstance(item, dict):
            continue
        required = ("type", "location", "severity", "evidence", "confidence")
        if not all(isinstance(item.get(key), (str, int, float)) for key in required):
            continue
        location = str(item["location"])
        path = location.split(":", 1)[0]
        severity = str(item["severity"]).lower()
        if path not in known_paths or severity not in {"low", "medium", "high", "critical"}:
            continue
        findings.append(
            Finding(
                type=str(item["type"]).strip(),
                location=location,
                severity=severity,
                evidence=str(item["evidence"]).strip(),
                confidence=float(item["confidence"]),
            )
        )
    return findings


def _prompt(chunks: list[SourceChunk], lessons: list[str]) -> tuple[str, str]:
    system = (
        "You are performing an authorized, defensive static security review of application code. Analyze only the code provided. "
        "Identify observable secure-coding risks in Android configuration, code, storage, IPC, networking, or WebViews. "
        "Do not provide exploit steps, payloads, or instructions for attacking an app. Each finding must be independently supported by evidence. "
        + FINDING_SCHEMA
    )
    lesson_context = ""
    if lessons:
        lesson_context = "\nGeneral security lessons to consider (they are hypotheses, not proof):\n- " + "\n- ".join(lessons)
    source = "\n\n".join(
        f"FILE: {chunk.path}\nLINES: {chunk.start_line}-{chunk.end_line}\n{chunk.content}" for chunk in chunks
    )
    return system, f"Review this batch of decompiled Android app material.{lesson_context}\n\n{source}"


def scan(settings: Settings, model: LanguageModel, role: str, lessons: list[str] | None = None) -> Path:
    corpus_path = settings.app.workspace / "corpus.jsonl"
    if not corpus_path.is_file():
        raise FileNotFoundError("No corpus found. Run `python scanner.py ingest` first.")
    chunks = _load_chunks(corpus_path, settings.scan.max_scan_chunks)
    known_paths = {chunk.path for chunk in chunks}
    all_findings: list[Finding] = []
    raw_responses: list[dict[str, object]] = []
    for batch_number, batch in enumerate(_batches(chunks, settings.scan.max_chunks_per_request, settings.scan.max_request_chars), 1):
        system, user = _prompt(batch, lessons or [])
        try:
            response = model.complete(system, user)
        except PromptBlockedError as error:
            raw_responses.append({"batch": batch_number, "chunk_ids": [chunk.id for chunk in batch], "blocked": True, "block_reason": str(error)})
            continue
        raw_responses.append({"batch": batch_number, "chunk_ids": [chunk.id for chunk in batch], "response": response})
        try:
            all_findings.extend(_validate_findings(_extract_json(response), known_paths))
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            raw_responses[-1]["parse_error"] = str(error)
    deduplicated = {(finding.type.lower(), finding.location, finding.evidence): finding for finding in all_findings}
    output = {
        "role": role,
        "model": model.name,
        "lessons_applied": lessons or [],
        "chunks_scanned": len(chunks),
        "requests": len(raw_responses),
        "findings": [asdict(finding) for finding in deduplicated.values()],
        "raw_responses": raw_responses,
    }
    path = settings.app.workspace / f"{role}_scan.json"
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return path
