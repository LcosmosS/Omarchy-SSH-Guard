# Ruleset review and staged activation

**Observed 2026-10-27**: repository ruleset `SSH Guard Branch Rules` (ID `25995496`) has `enforcement: disabled`.

This document describes the snapshot observed from GitHub, not a change to live repository settings. Rulesets cannot be activated by merging configuration files. A repository administrator must change them in GitHub settings after reviewing live checks.

## Observed disabled rules

| Existing condition | Review |
| --- | --- |
| Target includes `~DEFAULT_BRANCH` and `~ALL` | Redundant, broad selection; scope to intended protected branch (usually `main`) rather than all development branches |
| Prohibit deletion and non-fast-forward changes | Keep for the protected branch |
| Require linear history | Keep; use squash/rebase merges |
| Require signed commits | Valuable, but verify every intended contributor can sign before enforcement |
| Require deployment success, empty environment list | Remove until a real security-related deployment environment/check exists |
| Pull requests; approvals = 0 | **Not** an independent approval requirement |
| Require CODEOWNER review | Potentially blocks maintainer-authored PRs when the only named owner is the author |
| Require resolution of review threads | Keep once reviewers and review process exist |
| Extra approval for unattributed changes | Review semantics and availability before activation |
| Required status checks, empty list | Add actual observed check names, not guessed workflow labels |
| Code scanning: CodeQL, `high_or_higher` security and `all` alerts | Run CodeQL successfully on `main` first; validate analysis coverage and available GitHub entitlement |
| Code quality severity = all | Ensure the feature is enabled and available; evaluate false positives and quota |
| Copilot code review on push and draft PRs | Evaluate feature availability, cost and privacy; not a substitute for human code-owner approval |
| No bypass actors | Retain if legitimate emergency recovery process is documented; do not casually grant bypass |

## Important independence constraint

PR #2 now **proposes** both `@LcosmosS` and `@LibertySquared` on each CODEOWNERS line. As of the 2026-10-27 verification, GitHub reports `write` permission for `LibertySquared`; the invitation has been accepted. The change exists only on PR #2's head branch, not on `main`. CODEOWNERS enforcement reads the **base branch** file; only after merge will it affect PRs targeting `main`.

A contributor cannot approve their own pull request. With two eligible owners listed on the same line, either owner can satisfy CODEOWNER review, so require **at least one approving review**, **approval by someone other than the last pusher**, and **dismissal of stale approvals after new commits** (`dismiss_stale_reviews_on_push: true`). Do **not** enable mandatory code-owner review until effective `write` permission, CODEOWNERS parsing, and an independent review path have been demonstrated. A review bot's endorsement does not satisfy independent human approval.

## Recommended staged rollout

1. **Before merging PR #2:** Verify collaborator access (`LibertySquared` has `write` as checked 2026-10-27), review CODEOWNERS syntax and permission eligibility, run the privacy, plugin and CodeQL checks for the **final** PR head, independently review all changes and obtain an actual eligible reviewer approval. Correct findings before merge. Leave the ruleset disabled.
2. **Merge PR #2 only after those gates pass** with the ruleset still disabled. This incorporates CODEOWNERS and workflow configuration into `main`.
3. **After merging:** Run `Privacy guard / privacy-audit`, `Read-only plugin tests / python-tests`, and CodeQL analyses for `python` and `actions` on `main`. Confirm CodeQL uploads succeed and check names appear as expected; CodeQL does not inspect QML.
4. Inspect the *observed* GitHub check-run names and configure required checks only after the workflows exist on `main`. Scope enforcement to `main`; do not inadvertently protect feature branches through `~ALL`.
5. Configure one required approval (`required_approving_review_count: 1`), required code-owner review, `require_last_push_approval: true`, and **`dismiss_stale_reviews_on_push: true`**. The last setting invalidates previous approvals after later pushes; last-pusher independence alone is not a substitute. Both code owners must have `write` access and GitHub must parse their assignments.
6. Remove the empty required-deployments rule. Disable unavailable or inappropriate quality/Copilot requirements; choose scan thresholds consistent with supported tooling. Validate signed-commit workflows.
7. Initially set `enforcement: evaluate` if supported. Verify routine contributor operations and intentionally failing PRs are recognized without deadlocking.
8. Set `active` only after independent review, dry-run checks, signing support, and a documented access-recovery process are demonstrated.
9. Reinspect the live ruleset API and protected-branch behavior after activation; record the actual state.
10. Independently review and address PR #3's source-port-zero and path-race test findings before merging it; privileged integration remains prohibited.

## PR sequencing and review responsibilities

- **PR #2:** LibertySquared's write access has been verified. Keep draft until current-head CI passes and the ownership policy is independently examined; then mark ready, request and receive an eligible independent review, and only then merge while enforcement remains disabled.
- **Ruleset:** Scope to `main`, delete empty deployment requirements, require the actual observed CI checks after workflows exist on `main`; stage evaluation and then activation after checking for deadlock and branch protection. Do not activate `~ALL` across development branches blindly.
- **PR #3:** Keep separate. Its initial automated review reports two issues: source port `0` accepted and a filesystem path-race regression test that can succeed without triggering the race. Independently verify and resolve these before calling PR #3 review-ready. Rerun CI, update branch as needed, and obtain an independent qualifying review after the ruleset is active.
- **Privileged v2:** Remains blocked due to evidence forgery, rollback lifecycle, transaction replay, and unverified power-loss recovery; neither PR authorizes deployment.

## Evidence and limits

The privacy workflow is a heuristic guardrail against *obvious* accidental disclosures, not comprehensive secret scanning. CodeQL covers Python and GitHub Actions configuration, not QML or host runtime. Branch rules do not secure existing release artifacts, Git history, workstation firewall state, or runtime keys.

Reference: [GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets), [CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).
