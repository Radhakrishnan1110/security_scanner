from __future__ import annotations

import json
import re
from pathlib import Path

from .config import Settings
from .models import LanguageModel
from .scan import scan


def _json_array(response: str) -> list[str]:
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", response, re.S)
    candidate = fenced.group(1) if fenced else response.strip()
    if not candidate.startswith("["):
        candidate = response[response.find("[") : response.rfind("]") + 1]
    lessons = json.loads(candidate)
    if not isinstance(lessons, list) or not all(isinstance(item, str) for item in lessons):
        raise ValueError("Teacher did not return a JSON array of lesson strings")
    return lessons


def generate_lessons(teacher: LanguageModel, teacher_scan_path: Path, output_path: Path) -> list[str]:
    findings = json.loads(teacher_scan_path.read_text(encoding="utf-8"))["findings"]
    system = (
        "You distill Android security-review findings into reusable lessons for another model. "
        "Return JSON only: an array of 5 to 15 concise rules. Rules must be generalizable across apps. "
        "Never mention a filename, line number, package name, exact value, component name, or this app."
    )
    response = teacher.complete(system, json.dumps(findings, indent=2))
    lessons = _json_array(response)
    if any(re.search(r"(?:\bline\s+\d+|\.smali|\.java|\.kt|AndroidManifest\.xml)", lesson, re.I) for lesson in lessons):
        raise ValueError("Teacher lessons were instance-specific; refusing to use them for the student rescan")
    output_path.write_text(json.dumps(lessons, indent=2), encoding="utf-8")
    return lessons


def run_learning_loop(settings: Settings, teacher: LanguageModel, student: LanguageModel) -> tuple[Path, Path]:
    teacher_scan = settings.app.workspace / "teacher_scan.json"
    if not teacher_scan.is_file():
        raise FileNotFoundError("Teacher scan missing. Run `scan --role teacher` first.")
    lessons_path = settings.app.workspace / "lessons.json"
    lessons = generate_lessons(teacher, teacher_scan, lessons_path)
    after_scan = scan(settings, student, "student_after", lessons)
    return lessons_path, after_scan
