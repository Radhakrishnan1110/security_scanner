# Submission notes

## Matching findings to the benchmark

The scanner does not see the list of expected InsecureShop vulnerabilities while it scans. After scanning, the evaluator compares each known vulnerability with the model findings and ranks up to three likely matches using the finding title and evidence. I then review those suggestions before counting them. I chose this approach because an LLM can use different words for the same issue, but it can also describe a related issue that should not count. For example, credentials exposed by a ContentProvider are different from credentials hardcoded in source code.

Each benchmark item can match one finding, and a finding can be used only once. Recall is the number of confirmed benchmark items divided by 19. This gives a checkable result without pretending that keyword matching is perfect. The limitation is that this is one app: an improvement after the lessons is useful evidence, but it does not prove that the lessons generalize. I would test that later on held-out APKs that were not used when creating the lessons.

## Handling a large application

For an app with more than one million lines of code, I would not send all source text to a model. First, a fast local pass would index manifests, exported components, permissions, network settings, API calls, and security-sensitive methods. It would split code by class or function, create small summaries, and keep a call graph or dependency map. The model would receive only the most relevant pieces of code, plus the small amount of surrounding context needed to understand a data flow.

The work can run in parallel by module or package. Results and summaries should be cached, duplicate findings should be merged, and every finding should keep links to the original files and lines. This makes the process cheaper, faster, and easier to review. High-risk areas such as authentication, WebViews, IPC, file handling, and network code should be scanned first, while lower-risk code can be processed later or on demand.

## Dynamic analysis

The dynamic-analysis design and diagram are in `docs/dynamic_analysis.md`. It uses clean emulators, disposable test accounts, an AI agent that navigates with UI information and controlled input, and runtime evidence such as logs and network traffic. A finding is confirmed only when the expected security outcome is observed, not simply because the app crashes.

One bug type that dynamic analysis can confirm and static APK analysis cannot is a backend authorization issue such as IDOR. For example, the agent can log in as test user A and then make a controlled request for test user B's order. If the backend returns user B's data, the authorization flaw is proven. Static code can suggest a risky request path, but it cannot prove how the live backend will authorize it.

## Models and results

The teacher model was Gemini 3.8 Flash. It was used to independently review findings and turn them into general Android security lessons. The student model was the open model `recursive/flint-v1.0:free` through OpenRouter. I kept this student model fixed for both the baseline and guided scans so that the before-and-after comparison measures the effect of the lessons rather than a model change.

The confirmed baseline recall was 10/19 (52.6%). The guided student recall was 11/19 (57.9%). The run used a 60-chunk scan budget because of free-tier request limits. The raw scan output, lesson file, and reviewed evaluation files are included in `runs/insecureshop/`.
