#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

VERSION=$(grep -E '^version\s*=' pyproject.toml | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
TAG="v${VERSION}"

echo "Releasing $TAG"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Uncommitted changes detected:"
  git status --short
  echo
  echo "Commit them first, then re-run this script."
  exit 1
fi

# 1) Upload code to GitHub  → triggers tests.yml
git push origin main

# 2) Create and push tag     → triggers publish.yml (if configured on tags)
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists locally. Aborting."
  exit 1
fi

git tag "$TAG"
git push origin "$TAG"

echo
echo "Done."
echo "- tests.yml should run from the push to main"
echo "- publish.yml should run from the tag $TAG"
