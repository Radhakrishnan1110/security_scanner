from __future__ import annotations

import argparse
import json
from pathlib import Path

from scanner.config import load_settings
from scanner.evaluate import evaluate
from scanner.ingest import ingest
from scanner.learn import run_learning_loop
from scanner.models import create_model
from scanner.scan import scan


def main() -> None:
    parser = argparse.ArgumentParser(description="Configurable APK security-scanning harness")
    parser.add_argument("--config", type=Path, default=Path("config.toml"), help="Path to the TOML configuration file")
    parser.add_argument("command", choices=("check-config", "ingest", "scan", "learn", "evaluate"), help="Harness command to execute")
    parser.add_argument("--source-dir", type=Path, help="Existing JADX/Apktool output; skips APK decompilation")
    parser.add_argument("--role", choices=("teacher", "student"), help="Model role for the scan command")
    parser.add_argument("--lessons", type=Path, help="JSON file containing general lessons for a guided student scan")
    parser.add_argument("--scan-file", type=Path, help="Scan JSON to evaluate")
    parser.add_argument("--ground-truth", type=Path, default=Path("ground_truth/insecureshop.json"), help="Ground-truth JSON")
    parser.add_argument("--confirmed-matches", type=Path, help="JSON object mapping ground-truth IDs to finding indexes")
    args = parser.parse_args()

    settings = load_settings(args.config)
    if args.command == "check-config":
        for role, model_config in (("teacher", settings.teacher), ("student", settings.student)):
            model = create_model(model_config)
            key_state = "present" if __import__("os").getenv(model_config.api_key_env) else "missing"
            print(f"{role}: {model.name} via {model_config.base_url} (API key: {key_state})")
        print(f"APK: {settings.app.apk_path}")
        print(f"Workspace: {settings.app.workspace}")
    elif args.command == "ingest":
        corpus = ingest(settings, args.source_dir)
        print(f"Wrote indexed source corpus: {corpus}")
    elif args.command == "scan":
        if not args.role:
            parser.error("scan requires --role teacher or --role student")
        lessons = json.loads(args.lessons.read_text(encoding="utf-8")) if args.lessons else []
        if not isinstance(lessons, list) or not all(isinstance(lesson, str) for lesson in lessons):
            parser.error("--lessons must contain a JSON array of strings")
        model = create_model(settings.teacher if args.role == "teacher" else settings.student)
        output = scan(settings, model, args.role, lessons)
        print(f"Wrote {args.role} scan: {output}")
    elif args.command == "learn":
        lessons, after_scan = run_learning_loop(settings, create_model(settings.teacher), create_model(settings.student))
        print(f"Wrote general lessons: {lessons}")
        print(f"Wrote guided student scan: {after_scan}")
    elif args.command == "evaluate":
        if not args.scan_file:
            parser.error("evaluate requires --scan-file")
        confirmed = json.loads(args.confirmed_matches.read_text(encoding="utf-8")) if args.confirmed_matches else None
        output = settings.app.workspace / f"{args.scan_file.stem}_evaluation.json"
        report = evaluate(args.scan_file, args.ground_truth, output, confirmed)
        print(f"Wrote evaluation: {output} (confirmed recall: {report['confirmed_recall']:.1%})")


if __name__ == "__main__":
    main()
