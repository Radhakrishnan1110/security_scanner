import json
import tempfile
import unittest
from pathlib import Path

from scanner.evaluate import evaluate


class EvaluateTests(unittest.TestCase):
    def test_creates_candidates_and_uses_only_confirmed_matches_for_recall(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scan = root / "scan.json"
            truth = root / "truth.json"
            output = root / "output.json"
            scan.write_text(json.dumps({"findings": [{"type": "Insecure WebView settings", "evidence": "JavaScript enabled"}]}))
            truth.write_text(json.dumps([{"id": "V17", "title": "Insecure WebView settings", "aliases": ["WebView", "javascript enabled"]}]))
            report = evaluate(scan, truth, output)
            self.assertEqual(report["confirmed_recall"], 0)
            self.assertEqual(report["candidate_matches_for_manual_review"][0]["candidates"][0]["finding_index"], 0)
            confirmed = evaluate(scan, truth, output, {"V17": 0})
            self.assertEqual(confirmed["confirmed_recall"], 1)


if __name__ == "__main__":
    unittest.main()
