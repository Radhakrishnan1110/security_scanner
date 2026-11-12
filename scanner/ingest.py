from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

from .config import Settings


TEXT_SUFFIXES = {".java", ".kt", ".smali", ".xml", ".json", ".properties", ".txt", ".gradle", ".cfg"}
PRIORITY_NAMES = {"AndroidManifest.xml", "strings.xml", "provider_paths.xml"}


@dataclass(frozen=True)
class SourceChunk:
    id: str
    path: str
    start_line: int
    end_line: int
    content: str


def _run_decompiler(apk_path: Path, output_dir: Path) -> Path:
    jadx = shutil.which("jadx")
    apktool = shutil.which("apktool")
    local_apktool = Path(__file__).resolve().parents[1] / "tools" / "apktool.jar"
    if jadx:
        command = [jadx, "--deobf", "--output-dir", str(output_dir), str(apk_path)]
    elif apktool:
        command = [apktool, "d", "--force", "--output", str(output_dir), str(apk_path)]
    elif local_apktool.is_file():
        command = ["java", "-jar", str(local_apktool), "d", "--force", "--output", str(output_dir), str(apk_path)]
    else:
        raise RuntimeError(
            "No APK decompiler found. Install JADX (recommended), Apktool, or place Apktool at tools/apktool.jar; alternatively pass --source-dir."
        )
    subprocess.run(command, check=True)
    return output_dir


def resolve_source_tree(settings: Settings, source_dir: Path | None = None) -> Path:
    if source_dir:
        source_dir = source_dir.resolve()
        if not source_dir.is_dir():
            raise FileNotFoundError(f"Decompiled source directory does not exist: {source_dir}")
        return source_dir
    apk_path = settings.app.apk_path
    if not apk_path.is_file():
        raise FileNotFoundError(
            f"APK not found at {apk_path}. Download the app APK, update app.apk_path, or pass --source-dir."
        )
    return _run_decompiler(apk_path, settings.app.workspace / "decompiled")


def _candidate_files(source_dir: Path) -> list[Path]:
    manifest = source_dir / "AndroidManifest.xml"
    package = ""
    if manifest.is_file():
        import re

        match = re.search(r'\bpackage="([^"]+)"', manifest.read_text(encoding="utf-8", errors="replace"))
        package = match.group(1).replace(".", "/") if match else ""

    def is_relevant(path: Path) -> bool:
        relative = path.relative_to(source_dir).as_posix()
        if path.name in PRIORITY_NAMES:
            return True
        if path.suffix.lower() in {".java", ".kt"}:
            return True
        if path.suffix.lower() == ".smali":
            return bool(package) and f"/{package}/" in f"/{relative}"
        return relative.startswith("res/xml/") or relative.startswith("res/values/")

    files = [
        path
        for path in source_dir.rglob("*")
        if path.is_file() and (path.suffix.lower() in TEXT_SUFFIXES or path.name in PRIORITY_NAMES) and is_relevant(path)
    ]
    return sorted(files, key=lambda path: (path.name not in PRIORITY_NAMES, str(path).lower()))


def _make_chunks(path: Path, source_dir: Path, max_chars: int) -> Iterator[SourceChunk]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    buffer: list[str] = []
    start_line = 1
    size = 0
    relative_path = path.relative_to(source_dir).as_posix()
    for line_number, line in enumerate(lines, 1):
        if buffer and size + len(line) > max_chars:
            content = "".join(buffer)
            identity = f"{relative_path}:{start_line}:{line_number - 1}:{hashlib.sha256(content.encode()).hexdigest()[:12]}"
            yield SourceChunk(identity, relative_path, start_line, line_number - 1, content)
            buffer, start_line, size = [], line_number, 0
        buffer.append(line)
        size += len(line)
    if buffer:
        content = "".join(buffer)
        identity = f"{relative_path}:{start_line}:{len(lines)}:{hashlib.sha256(content.encode()).hexdigest()[:12]}"
        yield SourceChunk(identity, relative_path, start_line, len(lines), content)


def ingest(settings: Settings, source_dir: Path | None = None) -> Path:
    root = resolve_source_tree(settings, source_dir)
    output_dir = settings.app.workspace
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks = [chunk for path in _candidate_files(root) for chunk in _make_chunks(path, root, settings.scan.max_chunk_chars)]
    corpus_path = output_dir / "corpus.jsonl"
    with corpus_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
    manifest = {
        "source_root": str(root),
        "corpus": str(corpus_path),
        "files": len(_candidate_files(root)),
        "chunks": len(chunks),
        "max_chunk_chars": settings.scan.max_chunk_chars,
    }
    (output_dir / "ingest_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return corpus_path
