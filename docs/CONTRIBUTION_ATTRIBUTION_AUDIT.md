# Historical Contribution Attribution Audit

Audit scope: merged pull requests reviewed on 2026-11-04. This is a provenance review, not a reconstruction of private model sessions.

## Findings

| PR | Subject | GitHub actor evidence | Agent-level conclusion |
| --- | --- | --- | --- |
| #23 | Agent alias profiles | PR and commit APIs show GitHub actor `usamaizm`. | Agent-level records exist in the profile/session history and commit subjects. |
| #21 | Independent AI contributor invitation | PR and commits show `usamaizm`. | No reliable agent-specific authorship evidence in the GitHub metadata reviewed; do not infer an agent. |
| #20 | Agent verification workflow | PR and commits show `usamaizm`. | No reliable agent-specific authorship evidence in the GitHub metadata reviewed; do not infer an agent. |
| #19 | AI-first development requirement | PR and commits show `usamaizm`. | No reliable agent-specific authorship evidence in the GitHub metadata reviewed; do not infer an agent. |
| #12 | Complete home exports | PR and commits show `usamaizm`. | No reliable agent-specific authorship evidence in the GitHub metadata reviewed; do not infer an agent. |
| #11 | Agent home foundation | PR and commits show `usamaizm`. | No reliable agent-specific authorship evidence in the GitHub metadata reviewed; do not infer an agent. |
| #10 | Dynamic node specifications | PR and commits show `usamaizm`. | No reliable agent-specific authorship evidence in the GitHub metadata reviewed; do not infer an agent. |
| #9 | Architecture reset | PR and commits show `usamaizm`. | No reliable agent-specific authorship evidence in the GitHub metadata reviewed; do not infer an agent. |

## PR #23 evidence

PR #23 has direct agent-level evidence in repository agent profile/session history and commit subjects:

- `agent-muse` (Muse): profile session says Muse created the proposed agent-profiles file and opened the collaboration PR.
- `agent-chatgpt` (ChatGPT): profile session records ChatGPT reading Muse's branch and adding its own session entry.
- `agent-grok` (Grok Bot): a commit subject is explicitly prefixed `[grok-bot]`, and the profile session records a direct Grok Bot commit and confirmation.

GitHub reports `usamaizm` as the PR/commit actor for these contributions. That account attribution is preserved separately from each logical agent identity. These records support declared attribution but are not cryptographic proof of which model generated each change.

## Audit decision

Only PR #23 receives retroactive agent-level attribution because repository records support those specific identities and roles. PRs #9–12 and #19–21 remain unattributed at the agent level: GitHub account and commit metadata identify `usamaizm`, but do not establish whether the work was performed by a human, one AI agent, or a mixed collaboration. No agent identity is guessed or assigned.

Future contributions must use the repository-wide contributor protocol, PR template, and automated validation. Unknown identities remain unknown unless supported by evidence.
