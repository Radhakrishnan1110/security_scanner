import json
import tempfile
import unittest
from pathlib import Path

from scanner.config import AppConfig, ModelConfig, ScanConfig, Settings
from scanner.scan import scan


class FakeModel:
    name = "fake-security-model"

    def complete(self, system_prompt, user_prompt):
        return json.dumps(
            {
                "findings": [
                    {
                        "type": "Insecure WebView settings",
                        "location": "src/Demo.smali:1-2",
                        "severity": "high",
                        "evidence": "JavaScript is enabled without a trust boundary.",
                        "confidence": 0.9,
                    }
                ]
            }
        )


class ScanTests(unittest.TestCase):
    def test_scan_writes_validated_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "corpus.jsonl").write_text(
                json.dumps(
                    {
                        "id": "demo",
                        "path": "src/Demo.smali",
                        "start_line": 1,
                        "end_line": 2,
                        "content": "invoke-virtual {p0}, Landroid/webkit/WebSettings;->setJavaScriptEnabled(Z)V",
                    }
                )
                + "\n"
            )
            model_config = ModelConfig("openai_compatible", "https://example.test", "fake", "UNUSED")
            settings = Settings(AppConfig(workspace / "app.apk", workspace), ScanConfig(12000, 1, 12000, 10, "low"), model_config, model_config)
            output = scan(settings, FakeModel(), "teacher")
            report = json.loads(output.read_text())
            self.assertEqual(report["model"], "fake-security-model")
            self.assertEqual(report["findings"][0]["severity"], "high")


if __name__ == "__main__":
    unittest.main()
