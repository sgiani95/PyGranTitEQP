#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

VERSION=$(grep -E '^version\s*=' pyproject.toml | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
TAG="v${VERSION}"

echo "Version: $VERSION"
echo

# Commit any pending changes automatically
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Committing current changes..."
  git add -A
  git commit -m "Update for ${VERSION}"
fi

echo "What do you want to do?"
echo "  1) Only upload changes to GitHub  (tests.yml)"
echo "  2) Upload changes AND release to PyPI  (tests.yml + publish.yml)"
echo
read -r -p "Choose [1/2]: " CHOICE

case "$CHOICE" in
  1)
    git push origin main
    echo
    echo "Done. Changes uploaded. tests.yml should run."
    ;;
  2)
    if git rev-parse "$TAG" >/dev/null 2>&1; then
      echo "Error: tag $TAG already exists."
      exit 1
    fi
    git push origin main
    git tag "$TAG"
    git push origin "$TAG"
    echo
    echo "Done."
    echo "- main pushed → tests.yml"
    echo "- tag $TAG pushed → publish.yml / PyPI"
    ;;
  *)
    echo "Invalid choice."
    exit 1
    ;;
esac
