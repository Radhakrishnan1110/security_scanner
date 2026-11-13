# Submission notes

## Question: What is your match function, and why did you choose it?

The scanner does not see the list of expected InsecureShop vulnerabilities while it scans. After scanning, the evaluator compares each known vulnerability with the model findings. It scores possible matches using overlap between the ground-truth title or aliases and the finding's type and evidence. It returns up to three candidates for each known vulnerability.

I review the candidates before counting them. A match is confirmed only when the finding describes the same issue and its evidence points to the related code or configuration. For example, credentials exposed by a ContentProvider are different from credentials hardcoded in source code.

Each benchmark item can match one finding, and a finding can be used only once. Recall is the number of confirmed benchmark items divided by 19. I chose this method because an LLM may use different wording for the same issue, while an automatic keyword match could incorrectly count two related issues as identical.

This is still one app and one benchmark. A recall improvement after lessons is useful evidence, but it cannot prove that the lessons generalize. I would test that using held-out APKs that were not used to create the lessons.

## Question: How would you handle a real app with more than one million lines of code?

I would not send the full codebase to a model. A fast local pass would first index manifests, exported components, permissions, network settings, API calls, and security-sensitive methods. It would split code by class or function, create small summaries, and retain a call graph or dependency map.

The model would receive only the highest-risk code and enough surrounding context to understand a data flow. The scanner could process modules or packages in parallel, cache file summaries, and merge duplicate findings. Every finding would retain links to the original file and line numbers so a reviewer can verify it.

Authentication, WebViews, IPC, file handling, and networking would be scanned first. Lower-risk code could run later or only when a related data flow reaches it. This controls cost and response size while keeping the important attack paths visible.

## Question: How would you extend this into dynamic analysis with a live backend?

The detailed dynamic-analysis write-up and diagram are in `docs/dynamic_analysis.md`. Each test job would begin with a clean emulator, a disposable test account, and a test backend. An AI agent would navigate through the app using the UI hierarchy, screenshots, deep links, and controlled form input.

It would track visited screens, login states, actions, exported-component routes, and backend endpoints. This shows what parts of the app were actually explored. A finding is confirmed only when the expected security outcome happens. A crash alone is not enough. The report would include the action trace, relevant logs or network records, and replay steps.

One bug type that dynamic analysis can confirm and static analysis cannot is a backend authorization issue such as IDOR. For example, the agent can log in as test user A and make a controlled request for test user B's order. If the backend returns user B's data, the authorization flaw is proven.

To scale, a scheduler would distribute jobs across prebuilt emulators. Each job would have a time limit and reset the emulator to a clean snapshot after it finishes. For SSL pinning, an authorized test build or runtime instrumentation would trust the test proxy certificate. Native pinning, root or debugger detection, and custom certificate checks are likely failure points, so the harness must record whether traffic interception worked.

## Question: Which models did you use, and why?

The teacher model was Gemini 3.8 Flash. It was used to independently review findings and turn them into general Android security lessons. The student model was the open model `recursive/flint-v1.0:free` through OpenRouter.

I kept the student model fixed for both the baseline and guided scans. This means the before-and-after comparison measures the effect of the lessons instead of a model change. These models also fit the available free-tier limits.

## Question: What was the open model's recall before and after the lessons?

The confirmed baseline recall was 10/19 (52.6%). The guided student recall was 11/19 (57.9%). The run used a 60-chunk scan budget because of free-tier request limits. The raw scan output, lesson file, and reviewed evaluation files are included in `runs/insecureshop/`.

## Optional question: Did you run the frontier scan on a real APK? What was real, what was noise, and what broke?

Yes. I ran the student scanner against the Cricfy v6.8 APK as a separate static-analysis check. It indexed 122 files into 564 chunks and scanned 60 chunks in 20 model requests. The model reported 30 findings.

After reviewing the evidence, I counted 7 as supported security risks. These included cleartext traffic, risky WebView permissions, unvalidated URL handling from intents or push data, and external URL launches without a clear allowlist. Ten findings were plausible but needed more context, and 13 were noise for this review, such as handler or memory-leak warnings, foreground-service API compatibility, and non-sensitive preference storage. The binary summary is 7 supported findings and 23 findings not counted as confirmed security issues.

Two model responses were malformed and skipped. The other limits were a 60-chunk free-tier budget, obfuscated Smali, and native libraries. These made the review incomplete and caused some generic Android quality warnings to appear as security findings. The full optional report is in `docs/frontier_scan.md`.
