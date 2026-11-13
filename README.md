# APK Security Scanner

This project is a small, reusable APK security-scanning harness built around the InsecureShop APK. It decompiles an APK, prepares the application material for review, asks an LLM to identify supported security findings, and records the results as JSON. The scanner is not tied to InsecureShop source paths, so the APK path, workspace, and model providers can be changed in `config.toml`.

## What is included

- APK ingestion from a local APK, including decompilation and source/resource indexing.
- A baseline student scan.
- A separate teacher scan that produces general Android security lessons.
- A guided student scan using the same student model as the baseline.
- A recall evaluator against the 19 vulnerabilities documented by InsecureShop.
- Tests for scan-output validation and recall calculation.
- A proposed dynamic-analysis architecture in `docs/dynamic_analysis.md`.


## Submission notes

[Open the Google Doc](https://docs.google.com/document/d/1ShnBIKyQA61HCCkmiXX-T7arVcmEnVj6KDV1CFMhJdQ/edit?usp=sharing)

## Scan results

The baseline and guided scans used the same student model (`recursive/flint-v1.0:free`) and the same scan budget of 60 source chunks. This keeps the comparison fair.

| Scan | Confirmed findings | Recall |
| --- | ---: | ---: |
| Baseline student | 10 of 19 | 52.6% |
| Guided student | 11 of 19 | 57.9% |

The guided scan found one additional confirmed vulnerability. The confirmation mappings are stored alongside the generated run artifacts. Candidate matching is automated, while the final mapping is reviewed manually so that similar but different weaknesses are not counted as the same vulnerability.

## Project layout

```text
security_scanner/
  scanner/                 Scanner implementation
  tests/                   Unit tests
  ground_truth/            Independent 19-item benchmark list
  docs/                    Matching notes and dynamic-analysis proposal
  runs/insecureshop/       Generated corpus, scans, lessons, and evaluations
  config.example.toml      Safe configuration template
  scanner.py               Command-line entry point
```

## Setup

Requirements:

- Python 3.11 or later
- An APK to scan
- API keys for the configured teacher and student models
- JADX or Apktool available locally for a fresh decompilation

Copy the example configuration and set API keys only as environment variables:

```powershell
Copy-Item config.example.toml config.toml
$env:GEMINI_API_KEY = "your-gemini-key"
$env:OPENROUTER_API_KEY = "your-openrouter-key"
python scanner.py check-config
```

`config.toml` and any credential files are intentionally excluded from version control and submission.

## Reproducing the workflow

From the `security_scanner` directory:

```powershell
python scanner.py ingest
python scanner.py scan --role student
python scanner.py scan --role teacher
python scanner.py learn
python scanner.py evaluate --scan-file runs/insecureshop/student_scan.json --confirmed-matches runs/insecureshop/baseline-confirmation.json
python scanner.py evaluate --scan-file runs/insecureshop/student_after_scan.json --confirmed-matches runs/insecureshop/manual-confirmation.json
python -m unittest discover -s tests -v
```

`learn` converts the teacher findings into general lessons and then runs the guided student scan. The evaluator produces candidate matches first. The JSON confirmation files record the reviewed matches used for the final recall figures.

## Important limitations

- The free-model scan budget was limited to 60 of 368 indexed chunks. The limit is configurable through `max_scan_chunks` in `config.toml`.
- Static analysis can identify risky code and configuration, but cannot prove a server-side authorization flaw or real network behavior by itself.
- LLM findings require evidence review. The evaluator therefore separates automated candidate ranking from final benchmark confirmation.

## Dynamic analysis

`docs/dynamic_analysis.md` describes how I would extend the scanner with resettable emulators, controlled test accounts, UI-driven exploration, runtime evidence collection, replay traces, and safe handling of SSL pinning in an authorized test environment.
