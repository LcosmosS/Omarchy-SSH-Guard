# Code ownership change log

This is a **human-readable governance record**, not a substitute for Git commit history, signed reviews, or enforced branch protection.

## Current and proposed ownership

| Area | Code owner | Reason |
| --- | --- | --- |
| Repository-wide fallback | `@LcosmosS` (verified write); `@LibertySquared` (verified write) | Identified repository administrator |
| `.github/`, including CODEOWNERS and workflows | `@LcosmosS` (currently eligible); `@LibertySquared` (proposed, pending write-access acceptance) | Review changes to workflow privileges and enforcement |
| CLI, scripts and tests | `@LcosmosS` (currently eligible); `@LibertySquared` (proposed, pending write-access acceptance) | Security-sensitive executable code and parsers |
| QML widgets and manifest | `@LcosmosS` (currently eligible); `@LibertySquared` (proposed, pending write-access acceptance) | Unsandboxed desktop plugin surface |
| Security documentation and threat model | `@LcosmosS` (currently eligible); `@LibertySquared` (proposed, pending write-access acceptance) | Policy and trust-boundary consistency |

**Invitation gate passed (2026-10-27):** GitHub currently reports `write` permission for `LibertySquared`. Both accounts are eligible code owners once this CODEOWNERS file reaches the base branch (`main`). This does not itself constitute review or enable the disabled ruleset. Authors cannot approve their own pull requests; automated reviews are not independent human approvals.

**Approval semantics:** Two owners on the same CODEOWNERS line mean **either** eligible owner can satisfy the code-owner requirement; they do not require both approvals. After independent review of this governance PR, configure `required_approving_review_count: 1`, `require_last_push_approval: true`, **and `dismiss_stale_reviews_on_push: true`**. The last setting is needed so approvals for earlier diffs do not survive subsequent pushes. These are *recommended future ruleset settings*, not live enforcement; verify the exact settings after activation.

## Change history

### 2026-10-27 — Initial code ownership governance

- Added `.github/CODEOWNERS` with a repository-wide fallback and explicit security-critical paths.
- Recorded the sole-maintainer limitation and the safe ruleset activation sequence.
- Added privacy, CodeQL, and dependency-update workflows on a dedicated governance PR.
- Production SSH/UFW deployment and v0.2 privileged evidence integration remain out of scope.

### 2026-10-27 — Stage LibertySquared as second code owner (pending)

- Staged `@LibertySquared` beside `@LcosmosS` on each CODEOWNERS pattern in PR #2; no other repository files or external identities are made code owners.
- Initial permission check returned `read`; a subsequent GitHub permission check on 2026-10-27 returned `write` after invitation acceptance.
- Both users are now proposed code owners in the PR branch, but the base branch has not yet adopted this file.
- This update does **not** activate repository rulesets, grant approval, or establish independent review. Request independent review after final CI and confirm CODEOWNERS resolution on `main` after merge.

## Required entry for future ownership changes

For each change to `.github/CODEOWNERS`, record:

1. Date and PR link.
2. Paths and previous/new owner GitHub handles (no private names or contact details).
3. Confirmation that each new owner has repository write access.
4. Rationale, approval identity and whether that reviewer is independent of the author.
5. Any corresponding repository-ruleset or required-check changes.

This log is maintained through reviewable PRs. Do not use it to store host identities, network source addresses, private logs, signing keys or operational evidence.
