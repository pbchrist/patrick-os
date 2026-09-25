---
name: web-build-release
version: 1
purpose: Ship website changes from brief to verified Railway production with the fewest practical dev cycles and exact-commit safety.
task_class: draft
stage: null
mechanism_agnostic: true
channel: null
project: null
outputs: release
dry_run_default: true
sends: false
inputs:
  - name: repo
    type: string
    required: true
    description: Git repository in owner/name form or an already checked-out repository path.
  - name: change_brief
    type: string
    required: true
    description: The requested site changes, constraints, and anything that must not change.
  - name: deployment_target
    type: string
    required: false
    description: staging, production, or both. Default is staging until explicit production approval.
---

# web-build-release

## Purpose

Take a website from a user brief to a verified release without turning every discovery into another dev cycle.
The skill is optimized for GitHub plus Railway, but the release discipline is portable.

The default operating model is:

1. Inspect once.
2. Lock the brief once.
3. Make one batched implementation pass.
4. Run deterministic QA.
5. Make at most one regression-fix pass before staging.
6. Deploy the exact tested commit to staging once.
7. Promote the exact tested tree to production only after explicit approval.
8. Verify the public production domain before saying it is live.

A dev cycle is not a thought. It is a code-change plus test plus deploy loop. Avoid unnecessary loops.

## Inputs

- `repo`: {{ repo }}
- `change_brief`: {{ change_brief }}
- `deployment_target`: {{ deployment_target }}. If absent, stop at verified staging.

## Prerequisites

- Read the current repository state before editing. Do not work from memory when the tree is available.
- Resolve the staging and production branches, Railway project, service IDs, domains, start command, healthcheck, and current deployment metadata.
- If a project reference exists under `references/`, use it for stable IDs, but resolve current commit SHAs at runtime.
- Confirm which service is staging and which is production. Environment names alone are not sufficient.
- Preserve known-good tags, frozen releases, and user-designated restore points.
- Production changes require explicit approval. Staging changes do not require a second approval when the user has already requested the build.
- Do not touch unrelated repositories, Railway services, gateways, model servers, browsers, or user processes.

## Procedure

### 1. Inspect once and build the change map

Before the first edit, inspect the live page, staging page, repository, relevant notes or patches, and current deployment state.
Translate the request into four buckets:

- MUST CHANGE: every requested functional, visual, copy, infrastructure, and responsive change.
- MUST PRESERVE: working behaviors, brand elements, protected sections, frozen releases, and production state.
- CANDIDATE PATCH ITEMS: KEEP, MODIFY, or REJECT. Never apply a large external patch wholesale without classification.
- QA TARGETS: concrete checks that prove the requested change and the preserved behavior both work.

If something is ambiguous but not blocking, make the most conservative implementation choice that preserves existing behavior instead of opening another question-and-answer cycle.
Do not introduce new product strategy during QA.

### 2. Enforce the development-cycle budget

Default budget before staging:

- Cycle 0: inspection and change map only.
- Cycle 1: one batched implementation pass containing all known requested work.
- Cycle 2: regression fixes only, and only for defects found by QA.

Do not deploy after each small fix. Do not use staging as a substitute for local checks.
If three or more defects share one cause, fix the cause rather than patching each breakpoint or component independently.

### 3. Isolate work from production

Use the staging branch or an isolated staging worktree. Keep `main` or the production branch unchanged while implementing.
Before editing, record the current staging SHA and production SHA.
If the work is a large rewrite, create or confirm a recoverable checkpoint before changing files.

### 4. Batch the implementation

Apply the entire change map in one pass wherever practical.
Keep technical QA changes separate from unsolicited editorial or product changes.
When modifying layout, prefer rules that solve a class of widths over breakpoint-by-breakpoint patches.
When adding dependencies, self-host critical runtime assets when reliability is part of the brief and verify every referenced file exists.

### 5. Run static QA before browser QA

Run the cheapest deterministic checks first:

- syntax checks for JavaScript or modules,
- `git diff --check`,
- expected files present,
- expected routes and assets return 200 locally,
- no unexpected external runtime dependencies,
- security headers and cache behavior when the server layer changed,
- source or config files that should be private are not publicly served.

A static failure goes back to Cycle 1 if implementation is still in progress, otherwise to the single regression-fix pass.

### 6. Run the responsive matrix once

For a public marketing site, default viewport matrix:

`320, 360, 375, 390, 430, 768, 834, 900, 1024, 1116, 1280, 1440`

At every width, check `scrollWidth === innerWidth`, header mode, menu mode, primary content width, embeds, dashboards, cards, and any component previously known to size strangely.
Test breakpoint boundaries explicitly instead of assuming nearby widths cover them.
Use a GPU-disabled browser for layout QA where possible so WebGL cannot stall the entire sweep.

### 7. Test behavior, not just screenshots

For every interactive feature changed, test the behavior that matters:

- auto-rotators must advance without a click,
- manual controls must still work,
- menus must open and close correctly,
- in-page links must land on the intended section,
- iframes and cross-window messages must still communicate,
- fallback states must render when heavy graphics fail,
- reduced-motion behavior must remain usable when relevant.

Run WebGL-specific tests separately from layout QA. Never kill the user's normal browser to recover a test harness. Kill only the spawned test process.

### 8. Commit and push the tested staging tree

Only after local QA passes:

1. Review the diff against the change map and MUST PRESERVE list.
2. Commit the complete tested staging tree once.
3. Push the staging branch.
4. Record the exact full commit SHA.

Do not call a pushed branch "deployed."

### 9. Deploy the exact staging commit to Railway

Deploy by exact service ID and exact commit SHA.
Do not trust a generic Railway `redeploy` when the goal is to ship a new Git commit. It may reuse the previous deployment snapshot.
For a new commit, use a deployment path that explicitly accepts the commit SHA, such as the Railway agent scoped to the exact staging service.

After triggering deployment, verify all of the following before moving on:

- deployment service ID is the staging service,
- deployment branch is the staging branch,
- deployment commit hash equals the expected SHA,
- status reaches `SUCCESS`,
- the public staging URL returns 200,
- required assets return 200,
- visible content markers prove the new build is actually being served,
- the changed interactive behavior works on the public staging URL,
- responsive smoke tests still pass on the public deployment.

Never infer success from a tool saying "deployment triggered."

### 10. Promote only after explicit production approval

When the user explicitly says to push live, promote the already-tested tree. Do not rebuild the feature set again.
Merge staging into the production branch, or reuse an existing production merge commit when its tree is byte-for-byte identical to the tested staging tree.
Before deployment, verify the production tree contains the staging commit or is tree-equal to it.

Deploy the exact production commit SHA to the exact production Railway service.
Do not touch the staging service during production promotion unless a rollback is required.

Verify before saying production is live:

- Railway production deployment status is `SUCCESS`,
- deployment metadata shows the intended production commit,
- the real production domain returns 200,
- the new content marker is present,
- critical assets return 200,
- one mobile and two desktop widths have no horizontal overflow,
- changed interactive behavior works on the production domain.

### 11. Use resilient tool fallback without creating a new code path

If the primary workstation relay fails, do not restart the user's machine or recreate the work from scratch.
Use an authorized secondary machine, existing Git clone, GitHub, and Tailscale as available.
Fetch the exact commit and continue from Git history.
When a remote tool fails after a side-effecting call, verify state before retrying.

### 12. Report state precisely

Use only these status words when they are true:

- IMPLEMENTED: code exists locally.
- TESTED: defined QA passed locally.
- PUSHED: Git remote contains the commit.
- STAGING LIVE: public staging serves the exact expected commit.
- PRODUCTION LIVE: public production serves the exact expected commit.

## Outputs

A release record containing:

- repository and branch names,
- starting and final commit SHAs,
- concise change map,
- local QA result,
- viewport matrix result,
- staging deployment ID and verified commit hash,
- staging URL and live verification result,
- production deployment ID and verified commit hash when approved,
- production domain verification result,
- anything intentionally deferred.

The release record should be short enough to scan in under a minute.

## Quality checks

- No production change occurred before explicit approval.
- The deployed commit hash matches the intended SHA, not merely the intended branch.
- No generic redeploy was mistaken for a fresh Git deployment.
- No unrelated Railway service or local process was changed.
- All requested changes appear in the change map and are accounted for in the final diff.
- All MUST PRESERVE items still work.
- Responsive QA includes the exact breakpoint boundaries where navigation or layout mode changes.
- Interactive features are tested for autonomous behavior, not only clickable fallback behavior.
- Public URLs, not only localhost, are checked before a live claim.
- A single failed browser test does not trigger broad unrelated edits. Diagnose the specific cause first.
- Development cycles stay within the default budget unless a real defect or changed user brief requires another cycle.

## Failure modes

- **Patch-as-authority.** A QA or review patch quietly rewrites product positioning. Classify patch items before applying them.
- **Micro-deploy loop.** Every small fix is deployed separately. Batch known work and run local QA first.
- **Breakpoint whack-a-mole.** One width fix breaks another. Prefer container, min-width, overflow, and grid rules that solve the class.
- **Rotator that is really tabs.** Controls change content but the timer never advances. Test time-based behavior without user input.
- **Stale Railway snapshot.** `redeploy` reports success but metadata still shows the old commit. Deploy by exact SHA.
- **Branch-name trust.** A service says `staging` or `main`, but the deployed hash is wrong. Commit metadata is authoritative.
- **Test harness becomes the outage.** Heavy headless WebGL pegs GPU or hangs the workstation. Separate layout QA and graphics QA.
- **User browser collateral damage.** Killing Chrome to recover automated QA destroys the user's session. Never do this.
- **False done.** Code is committed or deployment is triggered, but the public URL was never checked.
- **Tool timeout duplicate action.** A side-effecting tool times out and the action is repeated blindly. Verify state first.

## Escalation

Stop and ask the user only when:

- the requested change is technically impossible with the current stack,
- production promotion has not been explicitly approved,
- the target Railway service cannot be identified unambiguously,
- the current production tree contains unrelated changes that would ship with the promotion,
- a destructive infrastructure action outside the requested deployment is required,
- credentials or repository access are missing and no authorized fallback exists.

Do not escalate merely because a small implementation choice has more than one acceptable answer.

## Examples

Input:

`repo=pbchrist/iconic-intelligence`

`change_brief=Fix the use-case rotator, broaden WAC use cases, strengthen private-hosting positioning, incorporate the good parts of a QA patch, check weird sizing, and do not break working behavior.`

Correct execution excerpt:

```text
Cycle 0: inspect repo, patch, staging, production, Railway service mapping.
Cycle 1: batch rotator + use cases + privacy + selected QA/server changes + responsive hardening.
QA: static checks, 320-1440 layout sweep, autonomous rotator test, asset/header checks.
Cycle 2: only the overflow and timer defects found by QA.
Staging: commit once, push once, deploy exact staging SHA, verify public staging.
Production: wait for explicit approval, promote tested tree, deploy exact main SHA, verify iconic.onl.
```

Wrong execution: deploy each copy edit separately, use generic Railway redeploy for a new commit, or call the site live before checking the public domain.
