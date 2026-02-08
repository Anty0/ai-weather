---
allowed-tools: Bash(git tag:*), Bash(git push:*), Bash(git add:*), Bash(git commit:*), Bash(gh release create:*), Bash(gh run:*), Bash(gh run list:*), Bash(gh run watch:*), Edit, Read
description: Release a new version - bump version, commit, tag, push, create GitHub release
argument-hint: "[major|minor|patch]"
---

# Release

## Current State

- Current version in pyproject.toml: !`grep '^version' pyproject.toml`
- Latest git tag: !`git describe --tags --abbrev=0`
- Commits since last tag: !`git log $(git describe --tags --abbrev=0)..HEAD --oneline`
- Current branch: !`git branch --show-current`
- GitHub repo: !`gh repo view --json nameWithOwner -q .nameWithOwner`

## Instructions

Follow these steps precisely to create a new release.

### Step 1: Determine version bump

If `$ARGUMENTS` is one of `major`, `minor`, or `patch`, use that bump type.

Otherwise, analyze the commits since the last tag and determine the appropriate semantic version bump:
- **patch** (X.Y.Z → X.Y.Z+1): bug fixes, chores, docs, minor tweaks
- **minor** (X.Y.Z → X.Y+1.0): new features, API changes, user-facing improvements
- **major** (X.Y.Z → X+1.0.0): breaking changes, major reworks — always confirm with user before bumping major

Present the proposed new version to the user and ask them to confirm using `AskUserQuestion`.

### Step 2: Summarize changes

Write concise, user-facing bullet points for each meaningful change since the last tag. Use plain language, not raw commit messages. These will go into the GitHub release body.

### Step 3: Pick a release punch line

Come up with 3-4 funny, catchy, short names for this release based on the biggest or most interesting change. These should be in the style of:
- "Keepin' output in check"
- "Interactivity ^2"

Use `AskUserQuestion` to let the user pick one or write their own.

### Step 4: Execute the release

Do all of the following in order:

1. Edit `pyproject.toml` to update the `version` field to the new version
2. Stage and commit:
   ```
   git add pyproject.toml
   git commit -m "release X.Y.Z"
   ```
3. Tag: `git tag vX.Y.Z`
4. Push: `git push && git push --tags`

### Step 5: Create GitHub release

Create the release on GitHub. The title format is `X.Y.Z - Punch Line`. The body format is:

```
Changes:
- bullet point 1
- bullet point 2

**Full Changelog**: https://github.com/OWNER/REPO/compare/vOLD...vNEW
```

Use `gh release create` with `--title` and `--notes` flags. Pass the notes via a HEREDOC for correct formatting.

### Step 6: Wait for CI

After the release is pushed, watch GitHub Actions to make sure CI passes:

1. Wait a moment for workflows to trigger, then use `gh run list --limit 5` to find the runs triggered by the push
2. Use `gh run watch <run-id>` to monitor each workflow run (there may be multiple: lint, docker)

If all checks pass, report success with a link to the release.

If any check fails, explain what happened and recommend one of these recovery strategies:
- **Flaky/random failure**: Rerun with `gh run rerun <run-id>`
- **Real failure**: We need to scrap the release and fix the issue:
  1. Delete the GitHub release: `gh release delete vX.Y.Z --yes`
  2. Delete the remote tag: `git push --delete origin vX.Y.Z`
  3. Delete the local tag: `git tag -d vX.Y.Z`
  4. Remove the release commit: `git reset --hard HEAD~1 && git push --force`
  5. Fix the issue, then re-release with the same version
