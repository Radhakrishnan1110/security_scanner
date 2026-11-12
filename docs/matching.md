# How findings are matched

The scanner does not receive the list of 19 expected InsecureShop vulnerabilities. This is important because the scan should be based on the APK, not on the expected answers.

After a scan, the evaluator compares each known vulnerability with the scanner findings. It looks at the finding title and evidence and suggests up to three possible matches. These are only suggestions.

I review the suggestions before counting them. A match is confirmed only when the finding describes the same problem and the evidence points to the relevant code or configuration. Similar issues are not automatically treated as the same issue. For example, a ContentProvider leaking credentials is not the same as credentials hardcoded in source code.

Each known vulnerability can match one finding, and each finding can be used for only one known vulnerability. Confirmed recall is:

```text
confirmed known vulnerabilities / 19
```

This keeps the result honest. LLMs often use different names for the same issue, but they can also describe related issues that should not be counted as a match. The JSON confirmation files record the final reviewed matches, so the reported recall can be checked later.
