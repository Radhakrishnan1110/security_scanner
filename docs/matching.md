# Finding matching

Evaluation is intentionally separate from scanning. The scanner never receives the InsecureShop ground-truth list, so it cannot optimize its wording to the expected answers.

For each ground-truth vulnerability, the evaluator ranks up to three model findings using overlap between the ground-truth title/aliases and the finding's type/evidence. This produces candidates for human review, not an automatic result. A reviewer records a confirmed mapping from a ground-truth ID to one finding index. Each model finding can be confirmed for at most one ground-truth entry.

Confirmed recall is `unique confirmed ground-truth entries / total ground-truth entries`. Precision is reported separately as a manual finding disposition because a small, one-app benchmark does not make automatic false-positive classification trustworthy.

This approach favors honest measurement over an overconfident fuzzy matcher. It still has limits: related vulnerabilities such as unsafe implicit intents can share language, a model can describe a real flaw with an unexpected taxonomy, and one application cannot establish that a learned rule generalizes. In an interview or a larger evaluation, I would preregister aliases and have a second reviewer resolve disagreements blind to whether a finding was baseline or post-lesson.
