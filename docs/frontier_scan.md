# Optional frontier scan: Cricfy APK

I ran the student scanner against the Cricfy v6.8 APK as a separate static-analysis check. I did not attempt to exploit the app or interact with its backend.

## Run summary

- Indexed files: 122
- Indexed chunks: 564
- Chunks scanned: 60
- Model requests: 20
- Reported findings: 30
- Blocked requests: 0
- Malformed model responses: 2

The two malformed responses were skipped and recorded in the raw scan output. The scan therefore covered about 11% of the indexed chunks. This is a free-tier budget limit, so the result is a sample rather than full application coverage.

## Review result

I reviewed the 30 reported findings using the same evidence-first approach as the InsecureShop evaluation.

- 7 were supported security risks: cleartext traffic, broad WebView permissions, unvalidated URL handling from intents or push data, and external URL launching without a clear allowlist.
- 10 were plausible concerns that need more context before being called vulnerabilities. For example, a broad deep-link rule may be intentional for a media app, and a URL from a trusted backend may not be attacker-controlled.
- 13 were noise for this security review. These included handler or memory-leak warnings, foreground-service API compatibility, storing a non-sensitive Boolean in preferences, and hardcoded non-secret fallback URLs.

For the requested real-versus-noise summary, this is 7 supported findings and 23 findings that I did not count as confirmed security issues.

## What broke or limited the scan

The scanner did not crash, but two model responses could not be parsed and were skipped. The APK also contained obfuscated Smali and native libraries, which reduce the context available to a static language-model review. The 60-chunk cap further limited coverage. The main source of noise was that the model sometimes reported Android quality or compatibility issues without proving a security impact or an attacker-controlled path.

The local evidence is in `runs/test/student_scan.json` and `runs/test/ingest_manifest.json`.
